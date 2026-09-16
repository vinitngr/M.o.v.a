#include "mpu6050_driver.h"

#define REG_PWR_MGMT_1   0x6B
#define REG_ACCEL_XOUT_H 0x3B

Mpu6050Driver::Mpu6050Driver(I2cSocket* socket) : _socket(socket) {}

void Mpu6050Driver::init() {
    _socket->init();
    _socket->writeByte(REG_PWR_MGMT_1, 0x00); // wake up device
}

bool Mpu6050Driver::readRaw(int16_t& ax, int16_t& ay, int16_t& az,
                             int16_t& gx, int16_t& gy, int16_t& gz) {
    uint8_t buf[14];
    if (!_socket->readBytes(REG_ACCEL_XOUT_H, buf, 14)) return false;

    ax = (buf[0] << 8) | buf[1];
    ay = (buf[2] << 8) | buf[3];
    az = (buf[4] << 8) | buf[5];
    // buf[6],buf[7] = temperature, skipped
    gx = (buf[8] << 8) | buf[9];
    gy = (buf[10] << 8) | buf[11];
    gz = (buf[12] << 8) | buf[13];
    return true;
}