#ifndef SOCKET_MAPPING_H
#define SOCKET_MAPPING_H

#include <Arduino.h>

// Logical socket IDs (same numbering idea as simulation_flattened).
#define SOCKET_DIO_1 7
#define SOCKET_DIO_2 8
#define SOCKET_DIO_3 9

struct DioSocketMapping {
    uint8_t dio;
};

// ESP32-CAM (AI-Thinker) fixed camera pins — DO NOT reuse these:
// PWDN=32 XCLK=0 SIOD=26 SIOC=27 Y9=35 Y8=34 Y7=39 Y6=36
// Y5=21 Y4=19 Y3=18 Y2=5 VSYNC=25 HREF=23 PCLK=22 FLASH=4
//
// Free, non-strapping GPIOs on AI-Thinker ESP32-CAM: 2, 12, 13, 14.
// (12 and 15 are strapping pins; 4 = flash LED; 16 = PSRAM; 6-11 = flash.)
//
// DIO_1 -> GPIO13 : STREAM button (tactile, INPUT_PULLUP)
// DIO_2 -> GPIO14 : AI-mode button (tactile, INPUT_PULLUP)
// DIO_3 -> GPIO2  : STATUS LED (output, external LED + resistor)

static const DioSocketMapping DIO_SOCKET_1 = { 13 };
static const DioSocketMapping DIO_SOCKET_2 = { 14 };
static const DioSocketMapping DIO_SOCKET_3 = { 2 };

inline const DioSocketMapping* getDioSocketMapping(uint8_t socket) {
    switch (socket) {
        case SOCKET_DIO_1: return &DIO_SOCKET_1;
        case SOCKET_DIO_2: return &DIO_SOCKET_2;
        case SOCKET_DIO_3: return &DIO_SOCKET_3;
        default: return nullptr;
    }
}

#endif
