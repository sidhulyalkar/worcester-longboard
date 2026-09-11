#pragma once

#include <stdint.h>

#ifndef X1_HX711_SPS
#define X1_HX711_SPS 10
#endif

static_assert(X1_HX711_SPS == 10 || X1_HX711_SPS == 80,
              "X1_HX711_SPS must be 10 or 80 to match HX711 RATE hardware");

namespace x1fit {
constexpr uint16_t kHx711SamplesPerSecond = X1_HX711_SPS;

// Allow more than one nominal conversion period for small oscillator/channel skew.
// A failed channel is still bounded and can no longer freeze the logger forever.
constexpr uint32_t kSampleWaitTimeoutUs =
    (kHx711SamplesPerSecond == 80) ? 30000u : 150000u;
constexpr uint32_t kIdlePollDelayUs = 250u;
}  // namespace x1fit
