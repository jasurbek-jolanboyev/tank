#include "tank/indicator_manager.h"

namespace tank {
IndicatorState IndicatorManager::update(AlertState alert, bool measured, float distance,
                                        bool approaching, uint32_t lastSeen, uint32_t now) {
  if (!config_.enabled || !config_.valid() || alert != AlertState::DroneConfirmed ||
      now - lastSeen > config_.trackLostTimeoutMs) {
    near_ = false; return state_ = IndicatorState::Off;
  }
  if (measured) {
    if (!near_ && distance <= config_.nearEnterMeters) near_ = true;
    if (near_ && distance >= config_.nearExitMeters) near_ = false;
  } else near_ = false;
  const bool red = near_ && (!config_.requireApproachingForRed || approaching);
  return state_ = red ? IndicatorState::Red : IndicatorState::White;
}
}  // namespace tank

