#include "ranging/tf02_pro.h"
#include "esp_timer.h"

namespace tank {
bool Tf02Pro::begin() {
  uart_config_t config{};
  config.baud_rate = baud_;
  config.data_bits = UART_DATA_8_BITS;
  config.parity = UART_PARITY_DISABLE;
  config.stop_bits = UART_STOP_BITS_1;
  config.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
  config.source_clk = UART_SCLK_DEFAULT;
  return uart_driver_install(uart_, 512, 0, 0, nullptr, 0) == ESP_OK &&
         uart_param_config(uart_, &config) == ESP_OK &&
         uart_set_pin(uart_, tx_, rx_, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE) == ESP_OK;
}

bool Tf02Pro::feed(uint8_t byte, uint32_t timestampMs) {
  Tf02Frame frame;
  if (!parser_.feed(byte, frame)) return false;
  measurement_.distanceMeters = frame.distanceCentimeters / 100.0f;
  measurement_.signalStrength = frame.signalStrength;
  measurement_.temperatureC = frame.temperatureC;
  measurement_.timestampMs = timestampMs;
  measurement_.valid = true;
  return true;
}

bool Tf02Pro::update() {
  uint8_t bytes[32];
  const int count = uart_read_bytes(uart_, bytes, sizeof(bytes), 0);
  bool received = false;
  const uint32_t now = static_cast<uint32_t>(esp_timer_get_time() / 1000);
  for (int i = 0; i < count; ++i) received = feed(bytes[i], now) || received;
  return received;
}
}  // namespace tank
