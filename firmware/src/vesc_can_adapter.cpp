#include "vesc_can_adapter.hpp"
#ifdef ARDUINO_ARCH_ESP32
#include <driver/twai.h>
#include <cmath>

static constexpr uint8_t CAN_PACKET_SET_CURRENT = 1;
static constexpr uint8_t CAN_PACKET_SET_CURRENT_BRAKE = 2;

bool VescCanAdapter::begin(int tx_gpio, int rx_gpio, int bitrate) {
    if (bitrate != 500000) return false;
    twai_general_config_t g = TWAI_GENERAL_CONFIG_DEFAULT((gpio_num_t)tx_gpio,(gpio_num_t)rx_gpio,TWAI_MODE_NORMAL);
    twai_timing_config_t t = TWAI_TIMING_CONFIG_500KBITS();
    twai_filter_config_t f = TWAI_FILTER_CONFIG_ACCEPT_ALL();
    if (twai_driver_install(&g,&t,&f) != ESP_OK) return false;
    return twai_start() == ESP_OK;
}

bool VescCanAdapter::sendScaledInt32(uint8_t id, uint8_t packet, float value, float scale) {
    int32_t v = (int32_t)std::lround(value * scale);
    twai_message_t m{};
    m.identifier = ((uint32_t)packet << 8) | id;
    m.extd = 1;
    m.data_length_code = 4;
    m.data[0] = (uint8_t)((uint32_t)v >> 24);
    m.data[1] = (uint8_t)((uint32_t)v >> 16);
    m.data[2] = (uint8_t)((uint32_t)v >> 8);
    m.data[3] = (uint8_t)((uint32_t)v);
    return twai_transmit(&m, pdMS_TO_TICKS(2)) == ESP_OK;
}

bool VescCanAdapter::sendDriveCurrent(uint8_t id, float amps) {
    return sendScaledInt32(id,CAN_PACKET_SET_CURRENT,amps,1000.0f);
}
bool VescCanAdapter::sendBrakeCurrent(uint8_t id, float amps) {
    return sendScaledInt32(id,CAN_PACKET_SET_CURRENT_BRAKE,amps,1000.0f);
}
void VescCanAdapter::stop(uint8_t id) { sendDriveCurrent(id,0.0f); }
#else
bool VescCanAdapter::begin(int,int,int) { return false; }
bool VescCanAdapter::sendDriveCurrent(uint8_t,float) { return false; }
bool VescCanAdapter::sendBrakeCurrent(uint8_t,float) { return false; }
void VescCanAdapter::stop(uint8_t) {}
#endif
