#pragma once

#include "esp_err.h"
#include "esp_http_server.h"
#include "freertos/FreeRTOS.h"

namespace tank {

// Read-only SoftAP bridge for node health and the latest serial telemetry.
// Camera JPEGs remain owned by Ubuntu; this endpoint verifies node reachability.
class WifiApBridge final {
 public:
  bool begin(const char* ssid, const char* password);
  void publish(const char* json);
  static WifiApBridge* activeInstance() { return active_; }

 private:
  static esp_err_t healthHandler(httpd_req_t* request);
  static esp_err_t telemetryHandler(httpd_req_t* request);
  static WifiApBridge* active_;
  char latest_[1024]{};
  portMUX_TYPE lock_ = portMUX_INITIALIZER_UNLOCKED;
  httpd_handle_t server_{};
};

}  // namespace tank

extern "C" void tank_wifi_publish(const char* json);
