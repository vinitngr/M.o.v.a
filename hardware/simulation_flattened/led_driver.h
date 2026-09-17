#ifndef LED_DRIVER_H
#define LED_DRIVER_H

#include "dio_socket.h"

class LedDriver {
public:
    LedDriver(DioSocket* socket);

    void init();
    void setState(bool state);

private:
    DioSocket* _socket;
};

#endif