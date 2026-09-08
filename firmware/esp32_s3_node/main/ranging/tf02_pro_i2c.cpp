#include "ranging/tf02_pro_i2c.h"
#include "esp_timer.h"
namespace tank { namespace { uint32_t nowMs(){return static_cast<uint32_t>(esp_timer_get_time()/1000);} }
bool Tf02I2cBus::begin(){ i2c_config_t c{}; c.mode=I2C_MODE_MASTER;c.sda_io_num=sda_;c.scl_io_num=scl_;c.sda_pullup_en=GPIO_PULLUP_DISABLE;c.scl_pullup_en=GPIO_PULLUP_DISABLE;c.master.clk_speed=frequency_;
 return i2c_param_config(port_,&c)==ESP_OK&&i2c_driver_install(port_,I2C_MODE_MASTER,0,0,0)==ESP_OK; }
bool Tf02ProI2c::begin(){static constexpr uint8_t request[]={0x5A,0x05,0x00,0x01,0x60};
 if(i2c_master_write_to_device(port_,address_,request,sizeof(request),pdMS_TO_TICKS(50))!=ESP_OK)return false;
 requestedAt_=nowMs();awaitingResponse_=true;return true;}
bool Tf02ProI2c::update(){const uint32_t now=nowMs();if(!awaitingResponse_){static constexpr uint8_t request[]={0x5A,0x05,0x00,0x01,0x60};
 if(i2c_master_write_to_device(port_,address_,request,sizeof(request),pdMS_TO_TICKS(50))!=ESP_OK){++errors_;return false;}requestedAt_=now;awaitingResponse_=true;return false;}
 if(now-requestedAt_<100)return false;uint8_t bytes[9]{};awaitingResponse_=false;if(i2c_master_read_from_device(port_,address_,bytes,sizeof(bytes),pdMS_TO_TICKS(50))!=ESP_OK){++errors_;return false;}
 Tf02Frame frame{};bool parsed=false;for(auto b:bytes)parsed=parser_.feed(b,frame)||parsed;if(!parsed){++errors_;return false;}
 measurement_.distanceMeters=frame.distanceCentimeters/100.0f;measurement_.signalStrength=frame.signalStrength;measurement_.temperatureC=frame.temperatureC;measurement_.timestampMs=now;measurement_.valid=true;return true;}
}  // namespace tank
