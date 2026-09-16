#include "distance_to_led_hook.h"

DistanceToLedHook::DistanceToLedHook(
    UltrasonicAdaptor* ultrasonic,
    LedAdaptor* led
)
    : _ultrasonic(ultrasonic),
      _led(led) {}

void DistanceToLedHook::init() {
}

void DistanceToLedHook::tick() {
    static bool ledState = false;

    float distance = _ultrasonic->getDistanceCm();

    if (!ledState && distance > 0 && distance < 45) {
        ledState = true;
        _led->on();
    }
    else if (ledState && distance > 55) {
        ledState = false;
        _led->off();
    }
}