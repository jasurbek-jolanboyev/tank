#pragma once
#include <cstdint>

namespace tank {
enum class ObjectClass : uint8_t { Drone, Bird, Aircraft, Person, UnknownAirObject };
enum class RangeClass : uint8_t { Unknown, Far, Medium, Near };

struct BoundingBox { float x{}; float y{}; float width{}; float height{}; };
struct Detection {
  uint32_t trackId{};
  ObjectClass objectClass{ObjectClass::UnknownAirObject};
  float confidence{};
  BoundingBox box{};
  uint32_t timestampMs{};
  bool simulated{};
};

inline bool valid(const BoundingBox& b) {
  return b.x >= 0 && b.y >= 0 && b.width > 0 && b.height > 0 &&
         b.x + b.width <= 1.0f && b.y + b.height <= 1.0f;
}
}  // namespace tank

