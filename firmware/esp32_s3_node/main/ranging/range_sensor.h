#pragma once

#include <cstdint>

namespace tank {
struct RangeMeasurement {
  float distanceMeters{};
  uint16_t signalStrength{};
  float temperatureC{};
  uint32_t timestampMs{};
  bool valid{};
};

class IRangeSensor {
 public:
  virtual ~IRangeSensor() = default;
  virtual bool begin() = 0;
  virtual bool update() = 0;
  virtual RangeMeasurement measurement() const = 0;
  virtual uint32_t errorCount() const = 0;
};
}  // namespace tank
