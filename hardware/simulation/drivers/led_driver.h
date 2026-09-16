#ifndef LED_DRIVER_H
#define LED_DRIVER_H

#include "driver_base.h"
#include "gpio_socket.h"

class LedDriver : public DriverBase {
public:
    LedDriver(GpioSocket* socket);

    void init() override;

    void setState(bool on);

private:
    GpioSocket* _socket;
};

#endif