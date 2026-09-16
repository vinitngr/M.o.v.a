#include "adaptor_registry.h"
#include <string.h>

void AdaptorRegistry::registerAdaptor(const char* name, void* adaptor) {
    if (_count >= MAX_ADAPTORS) return;

    _entries[_count].name = name;
    _entries[_count].adaptor = adaptor;
    _count++;
}

void* AdaptorRegistry::getAdaptor(const char* name) {
    for (int i = 0; i < _count; i++) {
        if (strcmp(_entries[i].name, name) == 0) {
            return _entries[i].adaptor;
        }
    }

    return nullptr;
}