idf_component_register(
  SRCS
    "app_main.cpp"
    "hardware/gpio_indicator_driver.cpp"
    "ranging/distance_filter.cpp"
    "ranging/tf02_pro.cpp"
    "ranging/tf02_pro_i2c.cpp"
    "transport/json_serial_transport.cpp"
    "network/wifi_ap_bridge.cpp"
    "core/src/sector.cpp"
    "core/src/temporal_validator.cpp"
    "core/src/indicator_manager.cpp"
    "core/src/tf02_frame_parser.cpp"
  INCLUDE_DIRS "." "core/include"
  REQUIRES driver esp_timer esp_system json nvs_flash esp_wifi esp_netif esp_event esp_http_server
)
if(DEFINED ENV{TANK_NODE_PROFILE})
  set(TANK_NODE_PROFILE_VALUE $ENV{TANK_NODE_PROFILE})
else()
  set(TANK_NODE_PROFILE_VALUE 1)
endif()
target_compile_definitions(${COMPONENT_LIB} PRIVATE TANK_NODE_PROFILE=${TANK_NODE_PROFILE_VALUE})
if(DEFINED ENV{TANK_INDICATOR_ACTIVE_HIGH})
  set(TANK_INDICATOR_ACTIVE_HIGH_VALUE $ENV{TANK_INDICATOR_ACTIVE_HIGH})
else()
  set(TANK_INDICATOR_ACTIVE_HIGH_VALUE 1)
endif()
target_compile_definitions(${COMPONENT_LIB} PRIVATE TANK_INDICATOR_ACTIVE_HIGH=${TANK_INDICATOR_ACTIVE_HIGH_VALUE})
