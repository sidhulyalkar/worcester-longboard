#pragma once
#include <cstdint>

// Worcester X1 Alpha defaults. Keep false until bench + wheel-off-ground commissioning.
#define X1_ALLOW_MOTOR_OUTPUT 0

static constexpr uint8_t X1_VESC_LEFT_ID = 10;
static constexpr uint8_t X1_VESC_RIGHT_ID = 11;
static constexpr int X1_CAN_TX_GPIO = 5;
static constexpr int X1_CAN_RX_GPIO = 6;

// Hall front-wheel inputs are placeholders and MUST be updated to actual harness pins.
static constexpr int X1_FRONT_HALL_L_GPIO = 9;
static constexpr int X1_FRONT_HALL_R_GPIO = 10;
