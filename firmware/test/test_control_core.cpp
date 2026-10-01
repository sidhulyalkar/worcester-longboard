#include "x1_control_core.hpp"
#include <cassert>
#include <cmath>
#include <iostream>

namespace {
bool near(float a, float b, float tol=1e-4f) {
    return std::fabs(a-b) <= tol;
}
}

int main() {
    x1::Config cfg;
    x1::Command prev{};
    x1::SensorFrame s;
    s.dt_s=0.1f; s.throttle=1.0f; s.remote_age_s=0; s.sensor_age_s=0;
    s.front_left_mps=s.front_right_mps=5.0f;
    s.rear_left_mps=6.2f; s.rear_right_mps=5.0f;
    auto c=x1::step_controller(cfg,x1::RideMode::Trail,s,prev);
    assert(c.drive_current_l_a < c.drive_current_r_a);
    assert(c.tc_scale_l < 0.5f);

    s.throttle=-1.0f; s.pack_voltage_v=58.15f;
    s.rear_left_mps=s.rear_right_mps=5.0f;
    c=x1::step_controller(cfg,x1::RideMode::Trail,s,prev);
    assert(c.mechanical_brake_recommended);
    assert(c.brake_current_l_a > 0.0f);

    s.remote_age_s=1.0f;
    c=x1::step_controller(cfg,x1::RideMode::Trail,s,prev);
    assert((c.faults & x1::FAULT_REMOTE_LOST) != 0);
    assert(c.brake_current_l_a == 0.0f && c.brake_current_r_a == 0.0f);

    // Provisional Shasta/companion envelope is deliberately below Learn mode.
    const auto shasta = x1::limits_for_mode(x1::RideMode::Shasta);
    const auto learn = x1::limits_for_mode(x1::RideMode::Learn);
    assert(near(shasta.speed_cap_mps, 2.70f));
    assert(near(shasta.accel_max_mps2, 0.45f));
    assert(near(shasta.decel_max_mps2, 0.80f));
    assert(near(shasta.phase_current_max_a, 18.0f));
    assert(near(shasta.drive_current_slew_max_a_per_s, 20.0f));
    assert(near(shasta.brake_current_slew_max_a_per_s, 30.0f));
    assert(near(shasta.fault_release_current_slew_a_per_s, 60.0f));
    assert(shasta.speed_cap_mps < learn.speed_cap_mps);
    assert(shasta.accel_max_mps2 < learn.accel_max_mps2);

    // Equal wheel state must produce symmetric companion-mode drive current.
    x1::SensorFrame dog{};
    dog.dt_s=0.1f;
    dog.throttle=1.0f;
    dog.front_left_mps=dog.front_right_mps=1.0f;
    dog.rear_left_mps=dog.rear_right_mps=1.0f;
    dog.remote_deadman_active=true;
    x1::Command zero{};
    c=x1::step_controller(cfg,x1::RideMode::Shasta,dog,zero);
    assert(near(c.drive_current_l_a, c.drive_current_r_a));
    // 20 A/s x 0.1 s = 2 A maximum first-step rise.
    assert(c.drive_current_l_a <= 2.0001f);
    assert(c.drive_current_l_a >= 0.0f);
    assert(c.lights_requested);

    // Deadman release must remove propulsion with the faster bounded fault ramp
    // and recommend independent mechanical stopping.
    x1::Command moving{};
    moving.drive_current_l_a=10.0f;
    moving.drive_current_r_a=10.0f;
    dog.remote_deadman_active=false;
    c=x1::step_controller(cfg,x1::RideMode::Shasta,dog,moving);
    assert((c.faults & x1::FAULT_DEADMAN_RELEASED) != 0);
    assert(near(c.drive_current_l_a, 4.0f));
    assert(near(c.drive_current_r_a, 4.0f));
    assert(c.mechanical_brake_recommended);
    assert(c.brake_current_l_a == 0.0f && c.brake_current_r_a == 0.0f);

    // Above the companion cap, positive throttle cannot increase propulsion.
    dog.remote_deadman_active=true;
    dog.front_left_mps=dog.front_right_mps=3.0f;
    dog.rear_left_mps=dog.rear_right_mps=3.0f;
    moving.drive_current_l_a=8.0f;
    moving.drive_current_r_a=8.0f;
    dog.throttle=1.0f;
    c=x1::step_controller(cfg,x1::RideMode::Shasta,dog,moving);
    assert((c.faults & x1::FAULT_OVERSPEED) != 0);
    assert(c.mechanical_brake_recommended);
    assert(c.drive_current_l_a < moving.drive_current_l_a);
    assert(c.drive_current_r_a < moving.drive_current_r_a);
    assert(near(c.drive_current_l_a, 2.0f));
    assert(near(c.drive_current_r_a, 2.0f));

    // Companion regen onset is slew-limited, not a current step.
    dog.front_left_mps=dog.front_right_mps=2.0f;
    dog.rear_left_mps=dog.rear_right_mps=2.0f;
    dog.throttle=-1.0f;
    dog.pack_voltage_v=50.4f;
    c=x1::step_controller(cfg,x1::RideMode::Shasta,dog,zero);
    assert(c.brake_current_l_a > 0.0f);
    assert(c.brake_current_r_a > 0.0f);
    // 30 A/s x 0.1 s = 3 A maximum first-step regen request.
    assert(c.brake_current_l_a <= 3.0001f);
    assert(c.brake_current_r_a <= 3.0001f);

    // Regen must drop immediately at the pack over-voltage ceiling.
    x1::Command braking{};
    braking.brake_current_l_a=6.0f;
    braking.brake_current_r_a=6.0f;
    dog.pack_voltage_v=cfg.regen_zero_voltage;
    c=x1::step_controller(cfg,x1::RideMode::Shasta,dog,braking);
    assert((c.faults & x1::FAULT_PACK_OVERVOLT) != 0);
    assert(c.brake_current_l_a == 0.0f);
    assert(c.brake_current_r_a == 0.0f);
    assert(c.mechanical_brake_recommended);

    std::cout << "X1 control-core tests PASS\n";
    return 0;
}
