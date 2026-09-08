#pragma once

#include <array>
#include <cstddef>

namespace tank {
class DistanceFilter {
 public:
  float update(float meters);
  bool hasValue() const { return initialized_; }
 private:
  std::array<float, 5> values_{};
  std::size_t count_{}, next_{};
  float ema_{};
  bool initialized_{};
};
}  // namespace tank
