#ifndef DIO_SOCKET_H
#define DIO_SOCKET_H

#include <Arduino.h>

class DioSocket {
public:
    DioSocket(uint8_t socket);

    void init(uint8_t mode);
    void write(uint8_t value);
    int read();

private:
    uint8_t _socket;
    uint8_t _pin;
};

#endif