#include <array>
#include <cstring>
#include "config/node_config.h"
#include "hardware/indicator_driver.h"
#include "ranging/distance_filter.h"
#include "ranging/tf02_pro_i2c.h"
#include "transport/json_serial_transport.h"
#include "esp_chip_info.h"
#include "esp_flash.h"
#include "esp_log.h"
#include "esp_psram.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

namespace { const char* TAG="tank-node"; uint32_t nowMs(){return static_cast<uint32_t>(esp_timer_get_time()/1000);} }

extern "C" void app_main(){
  using namespace tank; using namespace tank::node_config;
  esp_chip_info_t chip{};esp_chip_info(&chip);uint32_t flashBytes{};esp_flash_get_size(nullptr,&flashBytes);
  ESP_LOGI(TAG,"node=%s profile=%d keys=%u firmware=%s",kNodeId,TANK_NODE_PROFILE,kKeyCount,kFirmwareVersion);
  ESP_LOGI(TAG,"cores=%u flash=%lu psram=%s heap=%lu",chip.cores,static_cast<unsigned long>(flashBytes),esp_psram_is_initialized()?"yes":"no",static_cast<unsigned long>(esp_get_free_heap_size()));

  Tf02I2cBus rangeBus(kRangeI2cPort,kRangeSda,kRangeScl,kRangeI2cHz);
  std::array<Tf02ProI2c,kKeyCount> ranges{{
    {kRangeI2cPort,kKeys[0].rangeI2cAddress},{kRangeI2cPort,kKeys[1].rangeI2cAddress},
    {kRangeI2cPort,kKeys[2].rangeI2cAddress},{kRangeI2cPort,kKeys[3].rangeI2cAddress}}};
  std::array<GpioIndicatorDriver,kKeyCount> indicators{{
    {kKeys[0].whiteGpio,kKeys[0].redGpio},{kKeys[1].whiteGpio,kKeys[1].redGpio},
    {kKeys[2].whiteGpio,kKeys[2].redGpio},{kKeys[3].whiteGpio,kKeys[3].redGpio}}};
  std::array<DistanceFilter,kKeyCount> filters{};std::array<bool,kKeyCount> rangeReady{},indicatorReady{};
  std::array<IndicatorState,kKeyCount> states{};std::array<uint32_t,kKeyCount> lastCommand{};
  const bool busReady=rangeBus.begin();
  for(std::size_t i=0;i<kKeyCount;++i){indicatorReady[i]=indicators[i].begin();indicators[i].apply(IndicatorState::Off);rangeReady[i]=busReady&&ranges[i].begin();
    ESP_LOGI(TAG,"key=%s sector=%s range=%s indicator=%s i2c=0x%02x",kKeys[i].keyId,kKeys[i].sector,rangeReady[i]?"READY":"ERROR",indicatorReady[i]?"READY":"ERROR",kKeys[i].rangeI2cAddress);}
  JsonSerialTransport ubuntu(kUbuntuUart,kUbuntuRx,kUbuntuTx,kUbuntuBaud);const bool transportReady=ubuntu.begin();if(transportReady)setProtocolTransport(&ubuntu);
  uint32_t lastHealth{};
  while(true){
    const uint32_t now=nowMs();
    for(std::size_t i=0;i<kKeyCount;++i)if(rangeReady[i]&&ranges[i].update()){auto m=ranges[i].measurement();m.distanceMeters=filters[i].update(m.distanceMeters);sendRangeJson(kNodeId,kKeys[i].rangeSensorId,kKeys[i].sector,m);}
    IndicatorCommand command{};
    if(transportReady&&ubuntu.pollIndicator(command)){
      bool matched=false;for(std::size_t i=0;i<kKeyCount;++i)if(std::strcmp(command.sector,kKeys[i].sector)==0){states[i]=command.state;lastCommand[i]=now;indicators[i].apply(states[i]);matched=true;break;}
      if(!matched)ESP_LOGW(TAG,"rejected sector not owned by node: %s",command.sector);
    }
    for(std::size_t i=0;i<kKeyCount;++i)if(lastCommand[i]==0||now-lastCommand[i]>kUbuntuTimeoutMs){states[i]=IndicatorState::Off;indicators[i].apply(states[i]);}
    if(now-lastHealth>=1000){for(std::size_t i=0;i<kKeyCount;++i)sendHealthJson(kNodeId,kKeys[i].sector,states[i],rangeReady[i]&&ranges[i].errorCount()==0,indicatorReady[i],now);lastHealth=now;}
    vTaskDelay(pdMS_TO_TICKS(10));
  }
}
