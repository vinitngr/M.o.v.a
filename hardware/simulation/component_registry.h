#ifndef COMPONENT_REGISTRY_H
#define COMPONENT_REGISTRY_H

#include "component_mapping.h"
#include "adaptor_registry.h"

class ComponentRegistry {
public:
    ComponentRegistry(AdaptorRegistry* adaptorRegistry);

    void init();

    void* get(const char* name);

private:
    struct Entry {
        const char* name;
        const char* adaptor;
        uint8_t socket;
        void* adaptorObject;
    };

    static const int MAX_COMPONENTS = 20;

    Entry _components[MAX_COMPONENTS];
    int _count = 0;

    AdaptorRegistry* _adaptorRegistry;
};

#endif