#ifndef DISTANCE_TO_LED_HOOK_H
#define DISTANCE_TO_LED_HOOK_H

#include "hook_base.h"

class DistanceToLedHook : public HookBase {

public:

    DistanceToLedHook(
        ComponentRegistry* registry
    )
        : HookBase(registry) {
    }

    void init() override;
    void tick() override;
};

#endif