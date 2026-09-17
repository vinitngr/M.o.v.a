#include "dio_socket.h"
#include "socket_mapping.h"

DioSocket::DioSocket(uint8_t socket)
    : _socket(socket),
      _pin(255) {
}

void DioSocket::init(uint8_t mode) {
    const DioSocketMapping* mapping =
        getDioSocketMapping(_socket);

    if (mapping == nullptr) {
        return;
    }

    _pin = mapping->dio;

    pinMode(_pin, mode);
}

void DioSocket::write(uint8_t value) {
    if (_pin == 255) {
        return;
    }

    digitalWrite(_pin, value);
}

int DioSocket::read() {
    if (_pin == 255) {
        return -1;
    }

    return digitalRead(_pin);
}