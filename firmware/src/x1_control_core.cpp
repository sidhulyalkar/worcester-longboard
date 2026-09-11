#include "x1_control_core.hpp"
#include <algorithm>
#include <cmath>

namespace x1 {
namespace {
float clampf(float x, float lo, float hi) { return std::max(lo, std::min(hi, x)); }
float linear_derate(float value, float start, float zero) {
    if (value <= start) return 1.0f;
    if (value >= zero) return 0.0f;
    return (zero - value) / (zero - start);
}
float slew(float target, float prev, float rate, float dt) {
    const float d = std::max(0.0f, rate * dt);
    return clampf(target, prev-d, prev+d);
}
float slip_scale_drive(float slip, float begin, float full) {
    if (slip <= begin) return 1.0f;
    if (slip >= full) return 0.15f;
    const float t = (slip-begin)/(full-begin);
    return 1.0f - 0.85f*t;
}
float slip_scale_brake(float slip, float begin, float full) {
    if (slip >= begin) return 1.0f;
    if (slip <= full) return 0.10f;
    const float t = (begin-slip)/(begin-full);
    return 1.0f - 0.90f*t;
}
}

float kt_from_kv(float kv) { return 60.0f / (2.0f * 3.14159265358979323846f * kv); }

Limits limits_for_mode(RideMode mode) {
    switch (mode) {
        case RideMode::Learn: return {3.13f, 0.8f, 1.2f, 26.0f};
        case RideMode::Trail: return {6.26f, 1.4f, 1.9f, 48.0f};
        case RideMode::Flow:  return {8.94f, 2.0f, 2.4f, 65.0f};
        case RideMode::Sport: return {11.18f,2.7f, 2.8f, 75.0f};
    }
    return {3.13f, 0.8f, 1.2f, 26.0f};
}

State estimate_state(const Config& cfg, const SensorFrame& s) {
    State st;
    st.speed_mps = 0.5f * (s.front_left_mps + s.front_right_mps);
    const float denom = std::max(std::fabs(st.speed_mps), cfg.slip_min_speed_mps);
    st.slip_l = (s.rear_left_mps - st.speed_mps) / denom;
    st.slip_r = (s.rear_right_mps - st.speed_mps) / denom;
    if (s.remote_age_s > cfg.remote_timeout_s) st.faults |= FAULT_REMOTE_LOST;
    if (s.sensor_age_s > 0.10f) st.faults |= FAULT_SENSOR_STALE;
    if (s.batt_temp_c >= cfg.batt_derate_zero_c) st.faults |= FAULT_BATT_HOT;
    if (s.motor_temp_l_c >= cfg.motor_derate_zero_c) st.faults |= FAULT_MOTOR_HOT_L;
    if (s.motor_temp_r_c >= cfg.motor_derate_zero_c) st.faults |= FAULT_MOTOR_HOT_R;
    if (s.esc_temp_l_c >= cfg.esc_derate_zero_c) st.faults |= FAULT_ESC_HOT_L;
    if (s.esc_temp_r_c >= cfg.esc_derate_zero_c) st.faults |= FAULT_ESC_HOT_R;
    if (s.pack_voltage_v >= cfg.regen_zero_voltage) st.faults |= FAULT_PACK_OVERVOLT;
    return st;
}

Command step_controller(const Config& cfg, RideMode mode, const SensorFrame& s,
                        const Command& previous) {
    const Limits lim = limits_for_mode(mode);
    const State st = estimate_state(cfg, s);
    Command out;
    out.faults = st.faults;

    if ((st.faults & (FAULT_REMOTE_LOST | FAULT_SENSOR_STALE)) != 0) {
        out.drive_current_l_a = slew(0.0f, previous.drive_current_l_a, cfg.current_slew_a_per_s, s.dt_s);
        out.drive_current_r_a = slew(0.0f, previous.drive_current_r_a, cfg.current_slew_a_per_s, s.dt_s);
        out.mechanical_brake_recommended = true;
        return out;
    }

    const float thermal_batt = linear_derate(s.batt_temp_c, cfg.batt_derate_start_c, cfg.batt_derate_zero_c);
    const float thermal_l = std::min({thermal_batt,
        linear_derate(s.motor_temp_l_c,cfg.motor_derate_start_c,cfg.motor_derate_zero_c),
        linear_derate(s.esc_temp_l_c,cfg.esc_derate_start_c,cfg.esc_derate_zero_c)});
    const float thermal_r = std::min({thermal_batt,
        linear_derate(s.motor_temp_r_c,cfg.motor_derate_start_c,cfg.motor_derate_zero_c),
        linear_derate(s.esc_temp_r_c,cfg.esc_derate_start_c,cfg.esc_derate_zero_c)});

    const float kt = kt_from_kv(cfg.motor_kv);
    const float force_to_motor_current = cfg.wheel_radius_m /
        (2.0f * cfg.gear_ratio * cfg.drivetrain_eff * kt);

    if (s.throttle >= 0.0f) {
        float accel = s.throttle * lim.accel_max_mps2;
        const float headroom = lim.speed_cap_mps - st.speed_mps;
        accel *= clampf(headroom / 1.0f, 0.0f, 1.0f);
        float base_current = cfg.vehicle_mass_kg * accel * force_to_motor_current;
        base_current = clampf(base_current, 0.0f, lim.phase_current_max_a);

        const float tc_enable = clampf((std::fabs(st.speed_mps)-cfg.slip_min_speed_mps)/cfg.slip_min_speed_mps,0.0f,1.0f);
        out.tc_scale_l = (1.0f-tc_enable) + tc_enable*slip_scale_drive(st.slip_l,cfg.tc_begin_slip,cfg.tc_full_slip);
        out.tc_scale_r = (1.0f-tc_enable) + tc_enable*slip_scale_drive(st.slip_r,cfg.tc_begin_slip,cfg.tc_full_slip);

        const float target_l = base_current * out.tc_scale_l * thermal_l;
        const float target_r = base_current * out.tc_scale_r * thermal_r;
        out.drive_current_l_a = slew(target_l, previous.drive_current_l_a, cfg.current_slew_a_per_s, s.dt_s);
        out.drive_current_r_a = slew(target_r, previous.drive_current_r_a, cfg.current_slew_a_per_s, s.dt_s);
    } else {
        const float brake = -s.throttle;
        float decel = brake * lim.decel_max_mps2;
        float base_brake = cfg.vehicle_mass_kg * decel * force_to_motor_current;
        base_brake = clampf(base_brake, 0.0f, lim.phase_current_max_a);

        out.regen_scale_l = slip_scale_brake(st.slip_l,cfg.abs_begin_slip,cfg.abs_full_slip);
        out.regen_scale_r = slip_scale_brake(st.slip_r,cfg.abs_begin_slip,cfg.abs_full_slip);

        float vscale = 1.0f;
        if (s.pack_voltage_v >= cfg.regen_zero_voltage) vscale = 0.0f;
        else if (s.pack_voltage_v > cfg.regen_soft_voltage)
            vscale = (cfg.regen_zero_voltage - s.pack_voltage_v) /
                     (cfg.regen_zero_voltage - cfg.regen_soft_voltage);
        vscale = clampf(vscale,0.0f,1.0f);

        out.brake_current_l_a = base_brake * out.regen_scale_l * vscale * thermal_l;
        out.brake_current_r_a = base_brake * out.regen_scale_r * vscale * thermal_r;
        out.mechanical_brake_recommended = (vscale < 0.75f) ||
            (out.regen_scale_l < 0.5f) || (out.regen_scale_r < 0.5f);
    }
    return out;
}

} // namespace x1
