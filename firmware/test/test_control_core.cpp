#include "x1_control_core.hpp"
#include <cassert>
#include <iostream>

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

    std::cout << "X1 control-core tests PASS\n";
    return 0;
}
