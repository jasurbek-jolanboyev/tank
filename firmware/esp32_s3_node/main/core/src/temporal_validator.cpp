#include "tank/temporal_validator.h"

namespace tank {
AlertState TemporalValidator::observe(const Detection& d, uint32_t firstSeen) {
  lastSeenMs_ = d.timestampMs;
  if (d.objectClass != ObjectClass::Drone || d.confidence < config_.minimumConfidence || !valid(d.box)) {
    consecutive_ = 0;
    state_ = d.objectClass == ObjectClass::UnknownAirObject ? AlertState::UnknownObject : AlertState::AirObject;
    return state_;
  }
  if (trackId_ != d.trackId || d.timestampMs - firstCandidateMs_ > config_.confirmationWindowMs) {
    trackId_ = d.trackId; firstCandidateMs_ = d.timestampMs; consecutive_ = 1;
  } else if (consecutive_ < 255) {
    ++consecutive_;
  }
  const bool oldEnough = d.timestampMs - firstSeen >= config_.minimumTrackAgeMs;
  state_ = consecutive_ >= config_.minimumConsecutiveFrames && oldEnough
      ? AlertState::DroneConfirmed : AlertState::DroneCandidate;
  return state_;
}
AlertState TemporalValidator::update(uint32_t nowMs) {
  if (state_ != AlertState::NoObject && nowMs - lastSeenMs_ > config_.maximumGapMs) {
    consecutive_ = 0; state_ = AlertState::TrackLost;
  }
  return state_;
}
}  // namespace tank

