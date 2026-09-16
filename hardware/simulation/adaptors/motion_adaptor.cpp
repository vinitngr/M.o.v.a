#include "motion_adaptor.h"
#include <math.h>

MotionAdaptor::MotionAdaptor(Mpu6050Driver* driver) : _driver(driver) {}

void MotionAdaptor::init() {
    _driver->init();
}

bool MotionAdaptor::getAcceleration(float& ax, float& ay, float& az) {
    int16_t rax, ray, raz, gx, gy, gz;
    if (!_driver->readRaw(rax, ray, raz, gx, gy, gz)) return false;

    ax = rax / 16384.0; // LSB sensitivity for ±2g range
    ay = ray / 16384.0;
    az = raz / 16384.0;
    return true;
}

bool MotionAdaptor::isMoving(float threshold) {
    float ax, ay, az;
    if (!getAcceleration(ax, ay, az)) return false;

    float magnitude = sqrt(ax * ax + ay * ay + az * az);
    return fabs(magnitude - 1.0) > (threshold - 1.0);
}