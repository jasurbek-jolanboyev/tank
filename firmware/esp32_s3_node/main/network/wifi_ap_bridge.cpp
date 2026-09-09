#include "network/wifi_ap_bridge.h"

#include <cstring>

#include "esp_event.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_wifi.h"
#include "nvs_flash.h"

namespace tank {
namespace { 
const char* TAG = "tank-wifi"; 
}

WifiApBridge* WifiApBridge::active_ = nullptr;

bool WifiApBridge::begin(const char* ssid, const char* password) {
  // 1. NVS Flash Initializatsiyasi
  esp_err_t err = nvs_flash_init();
  if (err == ESP_ERR_NVS_NO_FREE_PAGES || err == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    if (nvs_flash_erase() != ESP_OK) return false;
    err = nvs_flash_init();
  }
  if (err != ESP_OK) return false;

  // 2. Network Interface va Event Loop Sozlash
  if (esp_netif_init() != ESP_OK) return false;
  err = esp_event_loop_create_default();
  if (err != ESP_OK && err != ESP_ERR_INVALID_STATE) return false;

  esp_netif_t* ap_netif = esp_netif_create_default_wifi_ap();
  if (ap_netif == nullptr) return false;

  // 3. Wi-Fi AP Konfiguratsiyasi
  wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT();
  if (esp_wifi_init(&init) != ESP_OK) return false;

  wifi_config_t config{};
  std::strncpy(reinterpret_cast<char*>(config.ap.ssid), ssid, sizeof(config.ap.ssid) - 1);
  config.ap.ssid_len = std::strlen(ssid);
  config.ap.channel = 1;
  config.ap.max_connection = 4;

  if (password != nullptr && std::strlen(password) >= 8) {
    std::strncpy(reinterpret_cast<char*>(config.ap.password), password, sizeof(config.ap.password) - 1);
    config.ap.authmode = WIFI_AUTH_WPA2_PSK;
  } else {
    config.ap.authmode = WIFI_AUTH_OPEN;
  }

  if (esp_wifi_set_mode(WIFI_MODE_AP) != ESP_OK ||
      esp_wifi_set_config(WIFI_IF_AP, &config) != ESP_OK ||
      esp_wifi_start() != ESP_OK) {
    return false;
  }

  // 4. HTTP Serverini Yuritish va Router URI Handlerni Ro'yxatdan O'tkazish
  httpd_config_t http = HTTPD_DEFAULT_CONFIG();
  http.server_port = 80;
  http.ctrl_port = 32768;

  if (httpd_start(&server_, &http) != ESP_OK) {
    ESP_LOGE(TAG, "Failed to start HTTP server instance");
    return false;
  }

  httpd_uri_t health{};
  health.uri = "/health";
  health.method = HTTP_GET;
  health.handler = healthHandler;
  httpd_uri_t telemetry{};
  telemetry.uri = "/telemetry";
  telemetry.method = HTTP_GET;
  telemetry.handler = telemetryHandler;

  if (httpd_register_uri_handler(server_, &health) != ESP_OK ||
      httpd_register_uri_handler(server_, &telemetry) != ESP_OK) {
    ESP_LOGE(TAG, "Failed to register HTTP endpoints");
    return false;
  }

  active_ = this;
  ESP_LOGI(TAG, "SoftAP started successfully. SSID=%s IP=192.168.4.1", ssid);
  return true;
}

void WifiApBridge::publish(const char* json) {
  if (json == nullptr) return;
  portENTER_CRITICAL(&lock_);
  std::strncpy(latest_, json, sizeof(latest_) - 1);
  latest_[sizeof(latest_) - 1] = '\0';
  portEXIT_CRITICAL(&lock_);
}

esp_err_t WifiApBridge::healthHandler(httpd_req_t* request) {
  const char body[] = "{\"status\":\"ok\",\"service\":\"tank-esp32\",\"ap\":\"192.168.4.1\"}";
  httpd_resp_set_type(request, "application/json");
  return httpd_resp_send(request, body, HTTPD_RESP_USE_STRLEN);
}

esp_err_t WifiApBridge::telemetryHandler(httpd_req_t* request) {
  char body[sizeof(latest_)]{};
  if (active_ != nullptr) {
    portENTER_CRITICAL(&active_->lock_);
    std::strncpy(body, active_->latest_, sizeof(body) - 1);
    portEXIT_CRITICAL(&active_->lock_);
  }
  if (body[0] == '\0') {
    std::strcpy(body, "{\"status\":\"waiting\"}");
  }
  httpd_resp_set_type(request, "application/json");
  return httpd_resp_send(request, body, HTTPD_RESP_USE_STRLEN);
}

}  // namespace tank

extern "C" void tank_wifi_publish(const char* json) {
  if (tank::WifiApBridge::activeInstance() != nullptr) {
    tank::WifiApBridge::activeInstance()->publish(json);
  }
}
