#pragma once
#include <cstdint>
#include "tank/temporal_validator.h"

namespace tank {
enum class IndicatorState { Off, White, Red };
struct AlertConfig {
  float nearEnterMeters{20.0f};
  float nearExitMeters{22.0f};
  bool requireApproachingForRed{false};
  bool enabled{true};
  uint32_t trackLostTimeoutMs{2000};
  bool valid() const { return nearEnterMeters > 0 && nearExitMeters > nearEnterMeters; }
};
class IndicatorManager {
 public:
  explicit IndicatorManager(AlertConfig config = {}) : config_(config) {}
  IndicatorState update(AlertState alert, bool measuredDistance, float distanceMeters,
                        bool approaching, uint32_t lastSeenMs, uint32_t nowMs);
  IndicatorState state() const { return state_; }
 private:
  AlertConfig config_;
  IndicatorState state_{IndicatorState::Off};
  bool near_{};
};
}  // namespace tank

