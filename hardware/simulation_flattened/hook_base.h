#ifndef HOOK_BASE_H
#define HOOK_BASE_H

#include "component_ref.h"
#include "component_registry.h"

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
    ComponentRef<T> use(const char* componentName) {
        return _registry->use<T>(componentName);
    }

    ComponentRegistry* _registry;
};

#endif
