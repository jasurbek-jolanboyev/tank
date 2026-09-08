#include "ranging/distance_filter.h"
#include <algorithm>
#include <cmath>

namespace tank {
float DistanceFilter::update(float meters) {
  if (meters <= 0 || meters > 500 || (initialized_ && std::fabs(meters - ema_) > 8.0f)) return ema_;
  values_[next_] = meters; next_ = (next_ + 1) % values_.size();
  if (count_ < values_.size()) ++count_;
  auto sorted = values_;
  std::sort(sorted.begin(), sorted.begin() + count_);
  const float sample = sorted[count_ / 2];
  ema_ = initialized_ ? 0.35f * sample + 0.65f * ema_ : sample;
  initialized_ = true;
  return ema_;
}
}  // namespace tank
