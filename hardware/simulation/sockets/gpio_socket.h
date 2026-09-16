#ifndef GPIO_SOCKET_H
#define GPIO_SOCKET_H

#include <Arduino.h>

class GpioSocket {
public:
    GpioSocket(uint8_t socket);

    void init(uint8_t signal, uint8_t mode);

    void write(uint8_t signal, uint8_t value);

    int read(uint8_t signal);

    unsigned long pulseInSignal(
        uint8_t signal,
        uint8_t state,
        unsigned long timeout
    );

private:
    uint8_t _socket;

    uint8_t getPin(uint8_t signal);
};

#endif