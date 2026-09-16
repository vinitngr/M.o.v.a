#include "motion_to_led_hook.h"

MotionToLedHook::MotionToLedHook(MotionAdaptor* motion, LedAdaptor* led)
    : _motion(motion), _led(led) {}

void MotionToLedHook::init() {
    // nothing extra; motion and led already init'd in sketch
}

void MotionToLedHook::tick() {
    if (_motion->isMoving()) {
        _led->on();
    } else {
        _led->off();
    }
}