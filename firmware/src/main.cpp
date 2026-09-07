#include <Arduino.h>
#include "x1_config.hpp"
#include "x1_control_core.hpp"
#include "vesc_can_adapter.hpp"

VescCanAdapter vesc;
x1::Config cfg;
x1::Command previous_cmd;
x1::RideMode mode = x1::RideMode::Learn;

static x1::SensorFrame acquire_frame() {
    x1::SensorFrame s;
    s.dt_s = 0.01f;
    s.throttle = 0.0f;
    s.pack_voltage_v = 50.4f;
    s.remote_age_s = 999.0f;
    s.sensor_age_s = 0.0f;
    return s;
}

void setup() {
    Serial.begin(115200);
    delay(300);
    const bool can_ok = vesc.begin(X1_CAN_TX_GPIO, X1_CAN_RX_GPIO);
    Serial.printf("X1 Alpha ECU: CAN=%s, motor_output=%d\n", can_ok?"OK":"FAIL", X1_ALLOW_MOTOR_OUTPUT);
}

void loop() {
    static uint32_t last_us = micros();
    const uint32_t now = micros();
    if (now - last_us < 10000) return;
    last_us += 10000;

    x1::SensorFrame s = acquire_frame();
    x1::Command cmd = x1::step_controller(cfg, mode, s, previous_cmd);

#if X1_ALLOW_MOTOR_OUTPUT
    if (cmd.brake_current_l_a > 0.01f) vesc.sendBrakeCurrent(X1_VESC_LEFT_ID, cmd.brake_current_l_a);
    else vesc.sendDriveCurrent(X1_VESC_LEFT_ID, cmd.drive_current_l_a);
    if (cmd.brake_current_r_a > 0.01f) vesc.sendBrakeCurrent(X1_VESC_RIGHT_ID, cmd.brake_current_r_a);
    else vesc.sendDriveCurrent(X1_VESC_RIGHT_ID, cmd.drive_current_r_a);
#else
    vesc.stop(X1_VESC_LEFT_ID);
    vesc.stop(X1_VESC_RIGHT_ID);
#endif
    previous_cmd = cmd;
}
