#include "gpio_socket.h"
#include "socket_mapping.h"

GpioSocket::GpioSocket(uint8_t socket)
    : _socket(socket) {
}

uint8_t GpioSocket::getPin(uint8_t signal) {
    const GpioSocketMapping* mapping =
        getGpioSocketMapping(_socket);

    if (mapping == nullptr) {
        return 255;
    }

    if (signal == 1) {
        return mapping->signal1;
    }

    if (signal == 2) {
        return mapping->signal2;
    }

    return 255;
}

void GpioSocket::init(uint8_t signal, uint8_t mode) {
    uint8_t pin = getPin(signal);

    if (pin != 255) {
        pinMode(pin, mode);
    }
}

void GpioSocket::write(uint8_t signal, uint8_t value) {
    uint8_t pin = getPin(signal);

    if (pin != 255) {
        digitalWrite(pin, value);
    }
}

int GpioSocket::read(uint8_t signal) {
    uint8_t pin = getPin(signal);

    if (pin != 255) {
        return digitalRead(pin);
    }

    return LOW;
}

unsigned long GpioSocket::pulseInSignal(
    uint8_t signal,
    uint8_t state,
    unsigned long timeout
) {
    uint8_t pin = getPin(signal);

    if (pin == 255) {
        return 0;
    }

    return pulseIn(pin, state, timeout);
}