#include "component_registry.h"
#include <string.h>

ComponentRegistry::ComponentRegistry(AdaptorRegistry* adaptorRegistry)
    : _adaptorRegistry(adaptorRegistry) {}

void ComponentRegistry::init() {
    _count = 0;

    for (int i = 0; i < COMPONENT_COUNT && i < MAX_COMPONENTS; i++) {

        void* adaptor =
            _adaptorRegistry->getAdaptor(COMPONENTS[i].adaptor);

        if (adaptor == nullptr) {
            continue;
        }

        _components[_count].name = COMPONENTS[i].name;
        _components[_count].adaptor = COMPONENTS[i].adaptor;
        _components[_count].socket = COMPONENTS[i].socket;
        _components[_count].adaptorObject = adaptor;

        _count++;
    }
}

void* ComponentRegistry::get(const char* name) {
    for (int i = 0; i < _count; i++) {
        if (strcmp(_components[i].name, name) == 0) {
            return _components[i].adaptorObject;
        }
    }

    return nullptr;
}