#include "component_registry.h"
#include <string.h>

ComponentRegistry::ComponentRegistry(
    AdaptorRegistry* adaptorRegistry
)
    : _count(0),
      _adaptorRegistry(adaptorRegistry) {
}

void ComponentRegistry::init() {
    _count = 0;

    for (
        uint8_t i = 0;
        i < COMPONENT_COUNT &&
        _count < MAX_COMPONENTS;
        i++
    ) {
        void* adaptor =
            _adaptorRegistry->create(
                COMPONENTS[i].adaptor,
                COMPONENTS[i].socket
            );

        if (adaptor == nullptr) {
            Serial.print("[ComponentRegistry] ERROR: Failed to create adaptor '");
            Serial.print(COMPONENTS[i].adaptor);
            Serial.print("' for component '");
            Serial.print(COMPONENTS[i].name);
            Serial.println("'");
            continue;
        }

        _components[_count].name =
            COMPONENTS[i].name;

        _components[_count].adaptor =
            COMPONENTS[i].adaptor;

        _components[_count].adaptorObject =
            adaptor;

        _count++;
    }
}

void* ComponentRegistry::get(
    const char* name
) {
    for (uint8_t i = 0; i < _count; i++) {
        if (
            strcmp(
                _components[i].name,
                name
            ) == 0
        ) {
            return _components[i].adaptorObject;
        }
    }

    Serial.print("[ComponentRegistry] ERROR: Component '");
    Serial.print(name);
    Serial.println("' not found");

    return nullptr;
}