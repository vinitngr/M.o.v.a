#ifndef HOOK_BASE_H
#define HOOK_BASE_H

#include "component_ref.h"

class ComponentRegistry;

class HookBase {

public:

    HookBase(ComponentRegistry* registry)
        : _registry(registry) {
    }

    virtual void init() = 0;
    virtual void tick() = 0;
    virtual ~HookBase() {}

protected:

    template <typename T>
    ComponentRef<T> use(const char* componentName);

    ComponentRegistry* _registry;
};

#endif