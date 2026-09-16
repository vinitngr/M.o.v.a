#ifndef ULTRASONIC_ADAPTOR_H
#define ULTRASONIC_ADAPTOR_H

#include "ultrasonic_driver.h"

class UltrasonicAdaptor {
public:
    UltrasonicAdaptor(UltrasonicDriver* driver);

    void init();
    float getDistanceCm();

private:
    UltrasonicDriver* _driver;
};

#endif