#pragma once

#include "driver/gpio.h"
#include "tank/indicator_manager.h"

namespace tank {
class IndicatorDriver {
 public:
  virtual ~IndicatorDriver() = default;
  virtual bool begin() = 0;
  virtual void apply(IndicatorState state) = 0;
};

class GpioIndicatorDriver final : public IndicatorDriver {
 public:
  GpioIndicatorDriver(gpio_num_t white, gpio_num_t red, bool activeHigh = true)
      : white_(white), red_(red), activeHigh_(activeHigh) {}
  bool begin() override;
  void apply(IndicatorState state) override;
 private:
  gpio_num_t white_, red_;
  bool activeHigh_;
};
}  // namespace tank
