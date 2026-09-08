#include "hardware/indicator_driver.h"

namespace tank {
bool GpioIndicatorDriver::begin() {
  gpio_config_t config{};
  config.pin_bit_mask = (1ULL << white_) | (1ULL << red_);
  config.mode = GPIO_MODE_OUTPUT;
  config.pull_up_en = GPIO_PULLUP_DISABLE;
  config.pull_down_en = GPIO_PULLDOWN_ENABLE;
  config.intr_type = GPIO_INTR_DISABLE;
  if (gpio_config(&config) != ESP_OK) return false;
  apply(IndicatorState::Off);
  return true;
}

void GpioIndicatorDriver::apply(IndicatorState state) {
  const int on = activeHigh_ ? 1 : 0;
  const int off = activeHigh_ ? 0 : 1;
  gpio_set_level(white_, state == IndicatorState::White ? on : off);
  gpio_set_level(red_, state == IndicatorState::Red ? on : off);
}
}  // namespace tank
