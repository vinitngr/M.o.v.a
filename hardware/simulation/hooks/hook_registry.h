#ifndef HOOK_REGISTRY_H
#define HOOK_REGISTRY_H

#include "hook_base.h"

#define MAX_HOOKS 10

class HookRegistry {
public:
    void registerHook(HookBase* hook);
    void initAll();
    void tickAll();

private:
    HookBase* _hooks[MAX_HOOKS];
    int _count = 0;
};

#endif