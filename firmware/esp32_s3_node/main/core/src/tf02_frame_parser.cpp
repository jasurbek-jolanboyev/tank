#include "tank/tf02_frame_parser.h"

namespace tank {
bool Tf02FrameParser::feed(uint8_t byte, Tf02Frame& output) {
  if (position_ == 0 && byte != 0x59) return false;
  if (position_ == 1 && byte != 0x59) {
    position_ = byte == 0x59 ? 1 : 0;
    return false;
  }
  frame_[position_++] = byte;
  if (position_ < frame_.size()) return false;
  position_ = 0;
  uint8_t checksum = 0;
  for (std::size_t i = 0; i < 8; ++i) checksum = static_cast<uint8_t>(checksum + frame_[i]);
  if (checksum != frame_[8]) { ++errors_; return false; }
  output.distanceCentimeters = frame_[2] | (static_cast<uint16_t>(frame_[3]) << 8);
  output.signalStrength = frame_[4] | (static_cast<uint16_t>(frame_[5]) << 8);
  const uint16_t temperature = frame_[6] | (static_cast<uint16_t>(frame_[7]) << 8);
  output.temperatureC = temperature / 8.0f - 256.0f;
  return output.distanceCentimeters > 0;
}
}  // namespace tank
