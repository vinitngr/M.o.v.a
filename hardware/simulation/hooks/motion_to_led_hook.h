#ifndef MOTION_TO_LED_HOOK_H
#define MOTION_TO_LED_HOOK_H

#include "hook_base.h"
#include "motion_adaptor.h"
#include "led_adaptor.h"

class MotionToLedHook : public HookBase {
public:
    MotionToLedHook(MotionAdaptor* motion, LedAdaptor* led);
    void init() override;
    void tick() override;

private:
    MotionAdaptor* _motion;
    LedAdaptor* _led;
};

#endif