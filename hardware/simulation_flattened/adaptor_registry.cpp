#include "adaptor_registry.h"
#include <string.h>

AdaptorRegistry::AdaptorRegistry()
    : _count(0) {
}

AdaptorRegistry& AdaptorRegistry::instance() {
    static AdaptorRegistry registry;
    return registry;
}

void AdaptorRegistry::registerAdaptor(
    const char* name,
    Factory factory
) {
    if (_count >= MAX_ADAPTORS) return;

    _entries[_count].name = name;
    _entries[_count].factory = factory;
    _count++;
}

void* AdaptorRegistry::create(
    const char* name,
    uint8_t socket
) {
    for (uint8_t i = 0; i < _count; i++) {

        if (strcmp(_entries[i].name, name) == 0) {
            return _entries[i].factory(socket);
        }
    }

    return nullptr;
}