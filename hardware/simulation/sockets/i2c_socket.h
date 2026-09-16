#ifndef I2C_SOCKET_H
#define I2C_SOCKET_H

#include <Arduino.h>

class I2cSocket {
public:
    I2cSocket(uint8_t socket, uint8_t address);

    void init();

    bool writeByte(
        uint8_t reg,
        uint8_t value
    );

    bool readBytes(
        uint8_t reg,
        uint8_t* buffer,
        uint8_t length
    );

private:
    uint8_t _socket;
    uint8_t _address;
    uint8_t _sda;
    uint8_t _scl;
};

#endif