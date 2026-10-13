#ifndef LED_DRIVER_H
#define LED_DRIVER_H

#include "dio_socket.h"

// Reused from simulation_flattened/led_driver.h (unchanged API).
class LedDriver {
public:
    LedDriver(DioSocket* socket);
    void init();
    void setState(bool state);

private:
    DioSocket* _socket;
};

#endif
