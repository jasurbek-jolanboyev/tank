#pragma once
#include "tank/detection.h"

namespace tank {
enum class AlertState { NoObject, UnknownObject, AirObject, DroneCandidate, DroneConfirmed, TrackLost, CameraError, AiError, LowMemory };
struct TemporalConfig {
  float minimumConfidence{0.70f};
  uint8_t minimumConsecutiveFrames{3};
  uint32_t confirmationWindowMs{1200};
  uint32_t minimumTrackAgeMs{250};
  uint32_t maximumGapMs{450};
};
class TemporalValidator {
 public:
  explicit TemporalValidator(TemporalConfig config = {}) : config_(config) {}
  AlertState observe(const Detection& detection, uint32_t trackFirstSeenMs);
  AlertState update(uint32_t nowMs);
 private:
  TemporalConfig config_;
  uint32_t trackId_{};
  uint32_t firstCandidateMs_{};
  uint32_t lastSeenMs_{};
  uint8_t consecutive_{};
  AlertState state_{AlertState::NoObject};
};
}  // namespace tank

