#ifndef SOCKET_MAPPING_H
#define SOCKET_MAPPING_H

#include <Arduino.h>

// Logical socket IDs
#define SOCKET_I2C_1   1
#define SOCKET_I2C_2   2
#define SOCKET_I2C_3   3

#define SOCKET_GPIO_1  4
#define SOCKET_GPIO_2  5
#define SOCKET_GPIO_3  6

#define SOCKET_DIO_1   7
#define SOCKET_DIO_2   8
#define SOCKET_DIO_3   9

// Physical board mapping
// signal1/signal2 are the signal pins of the physical socket.
struct GpioSocketMapping {
    uint8_t signal1;
    uint8_t signal2;
};

struct I2cSocketMapping {
    uint8_t sda;
    uint8_t scl;
};

struct DioSocketMapping {
    uint8_t dio;
};


// GPIO Socket 1
// LED uses signal 1 → GPIO 4
static const GpioSocketMapping GPIO_SOCKET_4 = {
    4,
    5
};


// GPIO Socket 2
// Ultrasonic uses:
// signal 1 → GPIO 6
// signal 2 → GPIO 7
static const GpioSocketMapping GPIO_SOCKET_5 = {
    6,
    7
};


// GPIO Socket 3
static const GpioSocketMapping GPIO_SOCKET_6 = {
    10,
    11
};


// I2C Socket 1
static const I2cSocketMapping I2C_SOCKET_1 = {
    8,
    9
};


// I2C Socket 2/3 are reserved
static const I2cSocketMapping I2C_SOCKET_2 = {
    255,
    255
};

static const I2cSocketMapping I2C_SOCKET_3 = {
    255,
    255
};


// DIO Socket 1
static const DioSocketMapping DIO_SOCKET_1 = {
    12
};


// DIO Socket 2
static const DioSocketMapping DIO_SOCKET_2 = {
    13
};


// DIO Socket 3
static const DioSocketMapping DIO_SOCKET_3 = {
    14
};


inline const GpioSocketMapping* getGpioSocketMapping(
    uint8_t socket
) {
    switch (socket) {
        case SOCKET_GPIO_1:
            return &GPIO_SOCKET_4;

        case SOCKET_GPIO_2:
            return &GPIO_SOCKET_5;

        case SOCKET_GPIO_3:
            return &GPIO_SOCKET_6;

        default:
            return nullptr;
    }
}


inline const I2cSocketMapping* getI2cSocketMapping(
    uint8_t socket
) {
    switch (socket) {
        case SOCKET_I2C_1:
            return &I2C_SOCKET_1;

        case SOCKET_I2C_2:
            return &I2C_SOCKET_2;

        case SOCKET_I2C_3:
            return &I2C_SOCKET_3;

        default:
            return nullptr;
    }
}


inline const DioSocketMapping* getDioSocketMapping(
    uint8_t socket
) {
    switch (socket) {
        case SOCKET_DIO_1:
            return &DIO_SOCKET_1;

        case SOCKET_DIO_2:
            return &DIO_SOCKET_2;

        case SOCKET_DIO_3:
            return &DIO_SOCKET_3;

        default:
            return nullptr;
    }
}

#endif