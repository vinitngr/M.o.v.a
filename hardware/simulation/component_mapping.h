#ifndef COMPONENT_MAPPING_H
#define COMPONENT_MAPPING_H

#include "socket_mapping.h"

struct ComponentConfig {
    const char* name;
    const char* adaptor;
    uint8_t socket;
};

static const ComponentConfig COMPONENTS[] = {
    { "led_1",        "led_adaptor",        SOCKET_GPIO_1 },
    { "ultrasonic_1", "ultrasonic_adaptor", SOCKET_GPIO_2 },
};

static const uint8_t COMPONENT_COUNT =
    sizeof(COMPONENTS) / sizeof(COMPONENTS[0]);

#endif