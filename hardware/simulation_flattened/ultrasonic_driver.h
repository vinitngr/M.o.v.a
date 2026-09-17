#ifndef ULTRASONIC_DRIVER_H
#define ULTRASONIC_DRIVER_H

#include "driver_base.h"
#include "gpio_socket.h"

class UltrasonicDriver : public DriverBase {
public:
    UltrasonicDriver(GpioSocket* socket);

    void init() override;

    float getDistanceCm();

private:
    GpioSocket* _socket;
};

#endif