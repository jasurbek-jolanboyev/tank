#pragma once

#include "driver/gpio.h"
#include "driver/uart.h"
#include "ranging/range_sensor.h"
#include "tank/tf02_frame_parser.h"

namespace tank {
class Tf02Pro final : public IRangeSensor {
 public:
  Tf02Pro(uart_port_t uart, gpio_num_t rx, gpio_num_t tx, int baud)
      : uart_(uart), rx_(rx), tx_(tx), baud_(baud) {}
  bool begin() override;
  bool update() override;
  RangeMeasurement measurement() const override { return measurement_; }
  uint32_t errorCount() const override { return parser_.errorCount(); }
  bool feed(uint8_t byte, uint32_t timestampMs);
 private:
  uart_port_t uart_;
  gpio_num_t rx_, tx_;
  int baud_;
  Tf02FrameParser parser_{};
  RangeMeasurement measurement_{};
};
}  // namespace tank
