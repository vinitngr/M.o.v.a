#ifndef MPU6050_DRIVER_H
#define MPU6050_DRIVER_H

#include "driver_base.h"
#include "i2c_socket.h"

class Mpu6050Driver : public DriverBase {
public:
    Mpu6050Driver(I2cSocket* socket);
    void init() override;
    bool readRaw(int16_t& ax, int16_t& ay, int16_t& az,
                 int16_t& gx, int16_t& gy, int16_t& gz);

private:
    I2cSocket* _socket;
};

#endif