#include "distance_to_led_hook.h"
#include "component_registry.h"

#include "ultrasonic_adaptor.h"
#include "led_adaptor.h"

void DistanceToLedHook::init() {
}

void DistanceToLedHook::tick() {
    static bool ledState = false;

    auto ultrasonic = _registry->use<UltrasonicAdaptor>("us1");

    auto led = _registry->use<LedAdaptor>("led_1");

    if (!ultrasonic || !led) {
        return;
    }

    float distance =
        ultrasonic->getDistanceCm();

    if (
        !ledState &&
        distance > 0 &&
        distance < 45
    ) {
        ledState = true;
        led->on();
    }
    else if (
        ledState &&
        distance > 55
    ) {
        ledState = false;
        led->off();
    }
}