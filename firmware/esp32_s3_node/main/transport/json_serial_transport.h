#pragma once

#include <cstddef>
#include "driver/uart.h"
#include "tank/indicator_manager.h"
#include "ranging/range_sensor.h"

namespace tank {
struct IndicatorCommand { char sector[16]{}; IndicatorState state{IndicatorState::Off}; uint32_t trackId{}; };
class JsonSerialTransport {
 public:
  JsonSerialTransport(uart_port_t uart, gpio_num_t rx, gpio_num_t tx, int baud)
      : uart_(uart), rx_(rx), tx_(tx), baud_(baud) {}
  bool begin();
  bool pollIndicator(IndicatorCommand& command);
  void write(const char* message);
 private:
  uart_port_t uart_;
  gpio_num_t rx_, tx_;
  int baud_;
  char line_[384]{};
  std::size_t used_{};
};

void setProtocolTransport(JsonSerialTransport* transport);
void sendRangeJson(const char* nodeId, const char* sensorId, const char* sector,
                   const RangeMeasurement& measurement);
void sendHealthJson(const char* nodeId, const char* sector, IndicatorState state,
                    bool rangeHealthy, bool indicatorHealthy, uint32_t uptimeMs);
}  // namespace tank
