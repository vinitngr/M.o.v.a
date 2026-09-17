#include "hook_registry.h"

void HookRegistry::registerHook(HookBase* hook) {
    if (_count < MAX_HOOKS) {
        _hooks[_count++] = hook;
    }
}

void HookRegistry::initAll() {
    for (int i = 0; i < _count; i++) _hooks[i]->init();
}

void HookRegistry::tickAll() {
    for (int i = 0; i < _count; i++) _hooks[i]->tick();
}