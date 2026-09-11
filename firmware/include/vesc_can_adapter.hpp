#pragma once
#include <cstdint>

class VescCanAdapter {
public:
    bool begin(int tx_gpio, int rx_gpio, int bitrate = 500000);
    bool sendDriveCurrent(uint8_t controller_id, float amps);
    bool sendBrakeCurrent(uint8_t controller_id, float amps);
    void stop(uint8_t controller_id);

private:
    bool sendScaledInt32(uint8_t controller_id, uint8_t packet_id, float value, float scale);
};
