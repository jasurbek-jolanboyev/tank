#include "transport/json_serial_transport.h"
#include <cstdio>
#include <cstring>
#include "cJSON.h"
#include "esp_log.h"
#include "esp_system.h"
#include "network/wifi_ap_bridge.h"

namespace tank {
namespace { const char* TAG = "protocol"; JsonSerialTransport* output{}; }
bool JsonSerialTransport::begin() {
  uart_config_t config{};
  config.baud_rate = baud_; config.data_bits = UART_DATA_8_BITS;
  config.parity = UART_PARITY_DISABLE; config.stop_bits = UART_STOP_BITS_1;
  config.flow_ctrl = UART_HW_FLOWCTRL_DISABLE; config.source_clk = UART_SCLK_DEFAULT;
  return uart_driver_install(uart_, 1024, 0, 0, nullptr, 0) == ESP_OK &&
         uart_param_config(uart_, &config) == ESP_OK &&
         uart_set_pin(uart_, tx_, rx_, UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE) == ESP_OK;
}
void JsonSerialTransport::write(const char* message) {
  tank_wifi_publish(message);
  uart_write_bytes(uart_, message, std::strlen(message));
  uart_write_bytes(uart_, "\n", 1);
}
bool JsonSerialTransport::pollIndicator(IndicatorCommand& command) {
  uint8_t bytes[64]; const int count = uart_read_bytes(uart_, bytes, sizeof(bytes), 0);
  for (int i = 0; i < count; ++i) {
    if (bytes[i] == '\n') {
      line_[used_] = 0; used_ = 0;
      cJSON* root = cJSON_Parse(line_); if (!root) continue;
      const cJSON* version = cJSON_GetObjectItem(root, "protocolVersion");
      const cJSON* type = cJSON_GetObjectItem(root, "type");
      const cJSON* sector = cJSON_GetObjectItem(root, "sector");
      const cJSON* color = cJSON_GetObjectItem(root, "color");
      const cJSON* white = cJSON_GetObjectItem(root, "white"); const cJSON* red = cJSON_GetObjectItem(root, "red");
      const cJSON* requestedState = cJSON_GetObjectItem(root, "state");
      const cJSON* track = cJSON_GetObjectItem(root, "trackId");
      const bool commandType = cJSON_IsString(type) &&
          (std::strcmp(type->valuestring, "indicator_state") == 0 ||
           std::strcmp(type->valuestring, "indicator_cmd") == 0);
      const bool stringState = cJSON_IsString(requestedState) &&
          (std::strcmp(requestedState->valuestring,"OFF")==0 ||
           std::strcmp(requestedState->valuestring,"WHITE")==0 ||
           std::strcmp(requestedState->valuestring,"RED")==0);
      const bool stringColor = cJSON_IsString(color) &&
          (std::strcmp(color->valuestring,"OFF")==0 ||
           std::strcmp(color->valuestring,"WHITE")==0 ||
           std::strcmp(color->valuestring,"RED")==0);
      const bool valid = cJSON_IsNumber(version) && version->valueint == 1 && commandType &&
          cJSON_IsString(sector) && std::strlen(sector->valuestring) < sizeof(command.sector) &&
          ((stringState || stringColor) ||
           (cJSON_IsBool(white) && cJSON_IsBool(red) && !(cJSON_IsTrue(white) && cJSON_IsTrue(red))));
      if (valid) {
        std::strncpy(command.sector,sector->valuestring,sizeof(command.sector)-1);
        const cJSON* state = stringState ? requestedState : color;
        command.state = (state != nullptr) ?
          (std::strcmp(state->valuestring,"RED")==0?IndicatorState::Red:std::strcmp(state->valuestring,"WHITE")==0?IndicatorState::White:IndicatorState::Off) :
          (cJSON_IsTrue(red)?IndicatorState::Red:cJSON_IsTrue(white)?IndicatorState::White:IndicatorState::Off);
        command.trackId = cJSON_IsNumber(track) ? static_cast<uint32_t>(track->valuedouble) : 0;
      }
      cJSON_Delete(root); if (valid) return true;
    } else if (used_ + 1 < sizeof(line_)) line_[used_++] = static_cast<char>(bytes[i]);
    else used_ = 0;
  }
  return false;
}
void setProtocolTransport(JsonSerialTransport* transport) { output = transport; }
void sendRangeJson(const char* nodeId, const char* sensorId, const char* sector, const RangeMeasurement& m) {
  char json[384]; std::snprintf(json, sizeof(json), "{\"protocolVersion\":1,\"type\":\"range\",\"timestamp\":%lu,\"nodeId\":\"%s\",\"sensorId\":\"%s\",\"sector\":\"%s\",\"distanceMeters\":%.2f,\"signalStrength\":%u,\"temperatureC\":%.1f,\"valid\":%s}",
           static_cast<unsigned long>(m.timestampMs), nodeId, sensorId, sector, m.distanceMeters,
           m.signalStrength, m.temperatureC, m.valid ? "true" : "false");
  if (output) output->write(json); else ESP_LOGI(TAG, "%s", json);
}
void sendHealthJson(const char* nodeId, const char* sector, IndicatorState state,
                    bool rangeHealthy, bool indicatorHealthy, uint32_t uptimeMs) {
  char json[384]; std::snprintf(json, sizeof(json), "{\"protocolVersion\":1,\"type\":\"node_health\",\"timestamp\":%lu,\"nodeId\":\"%s\",\"sector\":\"%s\",\"rangeSensorsHealthy\":%s,\"indicatorDriverHealthy\":%s,\"whiteLed\":%s,\"redLed\":%s,\"freeHeap\":%lu,\"uptime\":%lu}",
           static_cast<unsigned long>(uptimeMs), nodeId, sector, rangeHealthy ? "true" : "false",
           indicatorHealthy ? "true" : "false",
           state == IndicatorState::White ? "true" : "false",
           state == IndicatorState::Red ? "true" : "false",
           static_cast<unsigned long>(esp_get_free_heap_size()), static_cast<unsigned long>(uptimeMs));
  if (output) output->write(json); else ESP_LOGI(TAG, "%s", json);
}
}  // namespace tank
