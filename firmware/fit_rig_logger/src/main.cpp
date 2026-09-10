#include <Arduino.h>
#include <Wire.h>
#include <HX711.h>
#include <esp_timer.h>
#include <math.h>

namespace {
constexpr uint8_t kHxDout[4] = {4, 6, 8, 10};
constexpr uint8_t kHxSck[4]  = {5, 7, 9, 11};
constexpr uint8_t kSda = 17;
constexpr uint8_t kScl = 18;

constexpr uint8_t kIcmAddrA = 0x68;
constexpr uint8_t kIcmAddrB = 0x69;
constexpr uint8_t kWhoAmI = 0x75;
constexpr uint8_t kWhoAmIExpected = 0x47;
constexpr uint8_t kPwrMgmt0 = 0x4E;
constexpr uint8_t kAccelDataX1 = 0x1F;

HX711 scales[4];
uint8_t icmAddr = 0;

bool readReg(uint8_t addr, uint8_t reg, uint8_t &value) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr, static_cast<uint8_t>(1)) != 1) return false;
  value = Wire.read();
  return true;
}

bool writeReg(uint8_t addr, uint8_t reg, uint8_t value) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  Wire.write(value);
  return Wire.endTransmission() == 0;
}

bool findAndStartIcm() {
  for (uint8_t addr : {kIcmAddrA, kIcmAddrB}) {
    uint8_t who = 0;
    if (readReg(addr, kWhoAmI, who) && who == kWhoAmIExpected) {
      // Gyro low-noise (11b) + accel low-noise (11b).
      if (!writeReg(addr, kPwrMgmt0, 0x0F)) return false;
      delay(50);
      icmAddr = addr;
      return true;
    }
  }
  return false;
}

bool readStaticRollDeg(float &rollDeg) {
  if (!icmAddr) return false;
  Wire.beginTransmission(icmAddr);
  Wire.write(kAccelDataX1);
  if (Wire.endTransmission(false) != 0) return false;
  constexpr uint8_t n = 6;
  if (Wire.requestFrom(icmAddr, n) != n) return false;
  uint8_t b[n];
  for (uint8_t &v : b) v = Wire.read();

  const int16_t ax = static_cast<int16_t>((b[0] << 8) | b[1]);
  const int16_t ay = static_cast<int16_t>((b[2] << 8) | b[3]);
  const int16_t az = static_cast<int16_t>((b[4] << 8) | b[5]);
  (void)ax;
  if (ay == 0 && az == 0) return false;
  rollDeg = atan2f(static_cast<float>(ay), static_cast<float>(az)) * 180.0f / PI;
  return isfinite(rollDeg);
}

bool allLoadCellsReady() {
  for (auto &scale : scales) {
    if (!scale.is_ready()) return false;
  }
  return true;
}
}  // namespace

void setup() {
  Serial.begin(115200);
  delay(250);

  for (size_t i = 0; i < 4; ++i) {
    scales[i].begin(kHxDout[i], kHxSck[i]);
    scales[i].set_gain(128);
  }

  Wire.begin(kSda, kScl);
  Wire.setClock(400000);
  const bool imuOk = findAndStartIcm();

  Serial.println("# Worcester X1 Fit Rig v0.3 raw logger");
  Serial.print("# imu_icm42688=");
  Serial.println(imuOk ? "ok" : "missing");
  Serial.println("t_us,left_heel_raw,left_forefoot_raw,right_heel_raw,right_forefoot_raw,roll_deg,imu_ok");
}

void loop() {
  if (!allLoadCellsReady()) {
    delay(1);
    return;
  }

  long raw[4];
  for (size_t i = 0; i < 4; ++i) raw[i] = scales[i].read();

  float rollDeg = NAN;
  const bool imuOk = readStaticRollDeg(rollDeg);
  const int64_t tUs = esp_timer_get_time();

  Serial.printf("%lld,%ld,%ld,%ld,%ld,", tUs, raw[0], raw[1], raw[2], raw[3]);
  if (imuOk) Serial.printf("%.5f,1\n", rollDeg);
  else Serial.println("nan,0");
}
