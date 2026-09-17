#ifndef ADAPTOR_REGISTRY_H
#define ADAPTOR_REGISTRY_H

#include <Arduino.h>


class AdaptorRegistry {

public:

    using Factory = void* (*)(uint8_t socket);


    static AdaptorRegistry& instance();


    void registerAdaptor(
        const char* name,
        Factory factory
    );


    void* create(
        const char* name,
        uint8_t socket
    );


private:

    struct Entry {

        const char* name;

        Factory factory;
    };


    static const uint8_t MAX_ADAPTORS = 20;


    Entry _entries[MAX_ADAPTORS];

    uint8_t _count;


    AdaptorRegistry();
};

#endif