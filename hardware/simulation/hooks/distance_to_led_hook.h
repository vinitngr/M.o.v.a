#ifndef DISTANCE_TO_LED_HOOK_H
#define DISTANCE_TO_LED_HOOK_H

#include "hook_base.h"
#include "ultrasonic_adaptor.h"
#include "led_adaptor.h"

class DistanceToLedHook : public HookBase {
public:
    DistanceToLedHook(
        UltrasonicAdaptor* ultrasonic,
        LedAdaptor* led
    );

    void init() override;
    void tick() override;

private:
    UltrasonicAdaptor* _ultrasonic;
    LedAdaptor* _led;
};

#endif