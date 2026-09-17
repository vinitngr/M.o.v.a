#include "ultrasonic_driver.h"

UltrasonicDriver::UltrasonicDriver(GpioSocket* socket)
    : _socket(socket) {
}

void UltrasonicDriver::init() {
    _socket->init(1, OUTPUT);
    _socket->init(2, INPUT);

    _socket->write(1, LOW);
}

float UltrasonicDriver::getDistanceCm() {
    _socket->write(1, LOW);
    delayMicroseconds(2);

    _socket->write(1, HIGH);
    delayMicroseconds(10);
    _socket->write(1, LOW);

    unsigned long duration =
        _socket->pulseInSignal(
            2,
            HIGH,
            30000
        );

    if (duration == 0) {
        return -1.0;
    }

    return duration * 0.0343 / 2.0;
}