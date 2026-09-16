#ifndef TIMED_BLINK_HOOK_H
#define TIMED_BLINK_H

#include "hook_base.h"
#include "led_adaptor.h"

class TimedBlinkHook : public HookBase {
public:
    TimedBlinkHook(LedAdaptor* led);

    void init() override;
    void tick() override;

private:
    LedAdaptor* _led;

    unsigned long _startTime;
    unsigned long _lastToggle;
    unsigned long _interval;

    bool _started;
    bool _running;
};

#endif