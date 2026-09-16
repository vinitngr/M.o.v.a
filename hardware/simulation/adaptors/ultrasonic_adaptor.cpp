#include "ultrasonic_adaptor.h"

UltrasonicAdaptor::UltrasonicAdaptor(UltrasonicDriver* driver)
    : _driver(driver) {}

void UltrasonicAdaptor::init() {
    _driver->init();
}

float UltrasonicAdaptor::getDistanceCm() {
    return _driver->getDistanceCm();
}