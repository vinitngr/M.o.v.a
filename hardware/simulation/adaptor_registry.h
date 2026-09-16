#ifndef ADAPTOR_REGISTRY_H
#define ADAPTOR_REGISTRY_H

class AdaptorRegistry {
public:
    void registerAdaptor(const char* name, void* adaptor);
    void* getAdaptor(const char* name);

private:
    struct Entry {
        const char* name;
        void* adaptor;
    };

    static const int MAX_ADAPTORS = 20;

    Entry _entries[MAX_ADAPTORS];
    int _count = 0;
};

#endif