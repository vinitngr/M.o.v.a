#ifndef SERIAL_TEST_HOOK_H
#define SERIAL_TEST_HOOK_H

#include "hook_base.h"

// Pure testing hook (no backend, no WiFi).
// stream_btn press -> camera ON + LED ON  ("camera started")
// stream_btn again -> camera OFF + LED OFF ("camera stopped")
// ai_btn press     -> prints mode toggle
// while camera on  -> captures frames on an interval and logs their size
//
// Everything is visible on the Serial monitor. Replace this hook with the
// real application hook later; drivers/adaptors stay untouched.
class SerialTestHook : public HookBase {
public:
    SerialTestHook(ComponentRegistry* registry) : HookBase(registry) {}
    void init() override;
    void tick() override;

private:
    unsigned long _lastFrameAt = 0;
    uint32_t _frames = 0;
};

#endif
