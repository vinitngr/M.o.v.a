#ifndef COMPONENT_MAPPING_H
#define COMPONENT_MAPPING_H

#include "socket_mapping.h"

// Which adaptor + socket backs each named component.
// Camera has no DIO socket (socket=0 = fixed pins / virtual).
struct ComponentConfig {
    const char* name;
    const char* adaptor;
    uint8_t socket;
};

static const ComponentConfig COMPONENTS[] = {
    { "stream_btn",  "button_adaptor", SOCKET_DIO_1 },
    { "ai_btn",      "button_adaptor", SOCKET_DIO_2 },
    { "status_led",  "led_adaptor",    SOCKET_DIO_3 },
    { "esp32_camera","camera_adaptor", 0 },
};

static const uint8_t COMPONENT_COUNT =
    sizeof(COMPONENTS) / sizeof(COMPONENTS[0]);

#endif
