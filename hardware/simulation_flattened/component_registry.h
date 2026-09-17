#ifndef COMPONENT_REGISTRY_H
#define COMPONENT_REGISTRY_H

#include <Arduino.h>
#include "component_mapping.h"
#include "adaptor_registry.h"
#include "component_ref.h"

class ComponentRegistry {

public:

    ComponentRegistry(
        AdaptorRegistry* adaptorRegistry
    );

    void init();

    void* get(const char* name);

    template <typename T>
    ComponentRef<T> use(const char* name) {
        return ComponentRef<T>(
            static_cast<T*>(
                get(name)
            )
        );
    }

private:

    struct Entry {
        const char* name;
        const char* adaptor;
        void* adaptorObject;
    };

    static const uint8_t MAX_COMPONENTS = 20;

    Entry _components[MAX_COMPONENTS];

    uint8_t _count;

    AdaptorRegistry* _adaptorRegistry;
};

#endif