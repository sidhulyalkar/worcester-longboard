#pragma once
#include <cstdint>

namespace x1 {

enum class RideMode : uint8_t { Learn=0, Trail=1, Flow=2, Sport=3 };

enum FaultBits : uint32_t {
    FAULT_NONE          = 0,
    FAULT_REMOTE_LOST   = 1u << 0,
    FAULT_BATT_HOT      = 1u << 1,
    FAULT_MOTOR_HOT_L   = 1u << 2,
    FAULT_MOTOR_HOT_R   = 1u << 3,
    FAULT_ESC_HOT_L     = 1u << 4,
    FAULT_ESC_HOT_R     = 1u << 5,
    FAULT_PACK_OVERVOLT = 1u << 6,
    FAULT_SENSOR_STALE  = 1u << 7,
};

struct Config {
    float vehicle_mass_kg = 70.0f;        // generic light-rider Alpha baseline; override locally
    float wheel_radius_m = 0.1016f;
    float gear_ratio = 7.0f;
    float drivetrain_eff = 0.90f;
    float motor_kv = 160.0f;

    float tc_begin_slip = 0.10f;
    float tc_full_slip = 0.20f;
    float abs_begin_slip = -0.12f;
    float abs_full_slip = -0.25f;
    float slip_min_speed_mps = 1.0f;

    float regen_soft_voltage = 57.4f;
    float regen_zero_voltage = 58.2f;

    float motor_derate_start_c = 75.0f;
    float motor_derate_zero_c = 95.0f;
    float esc_derate_start_c = 75.0f;
    float esc_derate_zero_c = 100.0f;
    float batt_derate_start_c = 45.0f;
    float batt_derate_zero_c = 55.0f;

    float current_slew_a_per_s = 140.0f;
    float remote_timeout_s = 0.20f;
};

struct Limits {
    float speed_cap_mps;
    float accel_max_mps2;
    float decel_max_mps2;
    float phase_current_max_a;
};

struct SensorFrame {
    float dt_s = 0.01f;
    float throttle = 0.0f;
    float front_left_mps = 0.0f;
    float front_right_mps = 0.0f;
    float rear_left_mps = 0.0f;
    float rear_right_mps = 0.0f;
    float pack_voltage_v = 50.4f;
    float pack_soc = 0.5f;
    float batt_temp_c = 25.0f;
    float motor_temp_l_c = 25.0f;
    float motor_temp_r_c = 25.0f;
    float esc_temp_l_c = 25.0f;
    float esc_temp_r_c = 25.0f;
    float remote_age_s = 0.0f;
    float sensor_age_s = 0.0f;
};

struct State {
    float speed_mps = 0.0f;
    float slip_l = 0.0f;
    float slip_r = 0.0f;
    uint32_t faults = FAULT_NONE;
};

struct Command {
    float drive_current_l_a = 0.0f;
    float drive_current_r_a = 0.0f;
    float brake_current_l_a = 0.0f;
    float brake_current_r_a = 0.0f;
    float tc_scale_l = 1.0f;
    float tc_scale_r = 1.0f;
    float regen_scale_l = 1.0f;
    float regen_scale_r = 1.0f;
    bool mechanical_brake_recommended = false;
    uint32_t faults = FAULT_NONE;
};

Limits limits_for_mode(RideMode mode);
State estimate_state(const Config& cfg, const SensorFrame& s);
Command step_controller(const Config& cfg, RideMode mode, const SensorFrame& s,
                        const Command& previous);
float kt_from_kv(float kv);

} // namespace x1
