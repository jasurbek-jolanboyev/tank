#pragma once
#include <array>
#include "driver/gpio.h"
#include "driver/i2c.h"
#include "driver/uart.h"
#ifndef TANK_NODE_PROFILE
#define TANK_NODE_PROFILE 1
#endif
namespace tank::node_config {
inline constexpr char kFirmwareVersion[] = "0.2.0-8keys";
inline constexpr std::size_t kKeyCount = 4;
struct KeyConfig { const char* keyId; const char* sector; const char* rangeSensorId;
  uint8_t rangeI2cAddress; gpio_num_t whiteGpio; gpio_num_t redGpio; };
// UNVERIFIED BOARD PROFILE: verify every GPIO against the exact ESP32-S3 board.
#if TANK_NODE_PROFILE == 1
inline constexpr char kNodeId[] = "NODE-01";
inline constexpr std::array<KeyConfig, kKeyCount> kKeys{{
  {"KEYS-01","FRONT_1","RANGE-FRONT-1",0x10,GPIO_NUM_4,GPIO_NUM_5},
  {"KEYS-02","FRONT_2","RANGE-FRONT-2",0x11,GPIO_NUM_6,GPIO_NUM_7},
  {"KEYS-03","RIGHT_1","RANGE-RIGHT-1",0x12,GPIO_NUM_8,GPIO_NUM_9},
  {"KEYS-04","RIGHT_2","RANGE-RIGHT-2",0x13,GPIO_NUM_10,GPIO_NUM_11},
}};
#elif TANK_NODE_PROFILE == 2
inline constexpr char kNodeId[] = "NODE-02";
inline constexpr std::array<KeyConfig, kKeyCount> kKeys{{
  {"KEYS-05","REAR_1","RANGE-REAR-1",0x10,GPIO_NUM_4,GPIO_NUM_5},
  {"KEYS-06","REAR_2","RANGE-REAR-2",0x11,GPIO_NUM_6,GPIO_NUM_7},
  {"KEYS-07","LEFT_1","RANGE-LEFT-1",0x12,GPIO_NUM_8,GPIO_NUM_9},
  {"KEYS-08","LEFT_2","RANGE-LEFT-2",0x13,GPIO_NUM_10,GPIO_NUM_11},
}};
#else
#error "TANK_NODE_PROFILE must be 1 or 2"
#endif
inline constexpr i2c_port_t kRangeI2cPort=I2C_NUM_0;
inline constexpr gpio_num_t kRangeSda=GPIO_NUM_12, kRangeScl=GPIO_NUM_13;
inline constexpr uint32_t kRangeI2cHz=100000;
inline constexpr uart_port_t kUbuntuUart=UART_NUM_2;
inline constexpr gpio_num_t kUbuntuRx=GPIO_NUM_16, kUbuntuTx=GPIO_NUM_15;
inline constexpr int kUbuntuBaud=115200;
inline constexpr uint32_t kUbuntuTimeoutMs=2000;
inline constexpr char kApSsid[]="TANK-SECURE-NET";
inline constexpr char kApPassword[]="Tank12345678";
}  // namespace tank::node_config
