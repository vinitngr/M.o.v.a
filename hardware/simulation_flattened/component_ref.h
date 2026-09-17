#ifndef COMPONENT_REF_H
#define COMPONENT_REF_H

template <typename T>
class ComponentRef {
public:
    ComponentRef(T* component)
        : _component(component) {
    }

    T* operator->() const {
        return _component;
    }

    T& operator*() const {
        return *_component;
    }

    T* get() const {
        return _component;
    }

    bool valid() const {
        return _component != nullptr;
    }

    operator bool() const {
        return _component != nullptr;
    }

private:
    T* _component;
};

#endif