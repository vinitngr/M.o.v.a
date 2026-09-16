#ifndef MOTION_ADAPTOR_H
#define MOTION_ADAPTOR_H

#include "mpu6050_driver.h"

class MotionAdaptor {
public:
    MotionAdaptor(Mpu6050Driver* driver);
    void init();
    bool getAcceleration(float& ax, float& ay, float& az);
    bool isMoving(float threshold = 1.5); // in g, deviation from 1g rest

private:
    Mpu6050Driver* _driver;
};

#endif