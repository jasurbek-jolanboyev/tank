#pragma once
#include "driver/gpio.h"
#include "driver/i2c.h"
#include "ranging/range_sensor.h"
#include "tank/tf02_frame_parser.h"
namespace tank {
class Tf02I2cBus { public: Tf02I2cBus(i2c_port_t p,gpio_num_t d,gpio_num_t c,uint32_t f):port_(p),sda_(d),scl_(c),frequency_(f){} bool begin();
 private: i2c_port_t port_; gpio_num_t sda_,scl_; uint32_t frequency_; };
class Tf02ProI2c final:public IRangeSensor { public: Tf02ProI2c(i2c_port_t p,uint8_t a):port_(p),address_(a){} bool begin() override; bool update() override;
  RangeMeasurement measurement() const override{return measurement_;} uint32_t errorCount() const override{return errors_+parser_.errorCount();}
 private: i2c_port_t port_; uint8_t address_; uint32_t requestedAt_{}; uint32_t errors_{}; bool awaitingResponse_{}; Tf02FrameParser parser_{}; RangeMeasurement measurement_{}; };
}  // namespace tank
