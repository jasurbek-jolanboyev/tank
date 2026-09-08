#pragma once
#include <array>
#include <cstddef>
#include <cstdint>

namespace tank {
struct Tf02Frame {
  uint16_t distanceCentimeters{};
  uint16_t signalStrength{};
  float temperatureC{};
};

class Tf02FrameParser {
 public:
  bool feed(uint8_t byte, Tf02Frame& output);
  uint32_t errorCount() const { return errors_; }
 private:
  std::array<uint8_t, 9> frame_{};
  std::size_t position_{};
  uint32_t errors_{};
};
}  // namespace tank
