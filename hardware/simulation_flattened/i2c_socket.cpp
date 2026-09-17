#include "i2c_socket.h"

#include "socket_mapping.h"

#include <Wire.h>


I2cSocket::I2cSocket(
    uint8_t socket,
    uint8_t address
)
    : _socket(socket),
      _address(address),
      _sda(255),
      _scl(255) {
}


void I2cSocket::init() {
    const I2cSocketMapping* mapping =
        getI2cSocketMapping(_socket);

    if (mapping == nullptr) {
        return;
    }

    _sda = mapping->sda;
    _scl = mapping->scl;

    if (_sda != 255 && _scl != 255) {
        Wire.begin(_sda, _scl);
    }
}


bool I2cSocket::writeByte(
    uint8_t reg,
    uint8_t value
) {
    Wire.beginTransmission(_address);

    Wire.write(reg);
    Wire.write(value);

    return Wire.endTransmission() == 0;
}


bool I2cSocket::readBytes(
    uint8_t reg,
    uint8_t* buffer,
    uint8_t length
) {
    Wire.beginTransmission(_address);
    Wire.write(reg);

    if (Wire.endTransmission(false) != 0) {
        return false;
    }

    Wire.requestFrom(
        (int)_address,
        (int)length
    );

    for (uint8_t i = 0; i < length; i++) {
        if (!Wire.available()) {
            return false;
        }

        buffer[i] = Wire.read();
    }

    return true;
}