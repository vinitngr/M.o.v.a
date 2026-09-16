#ifndef HOOK_BASE_H
#define HOOK_BASE_H

class HookBase {
public:
    virtual void init() = 0;
    virtual void tick() = 0;
    virtual ~HookBase() {}
};

#endif