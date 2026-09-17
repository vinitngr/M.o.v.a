#ifndef DRIVER_BASE_H
#define DRIVER_BASE_H

class DriverBase {
public:
    virtual void init() = 0;
    virtual ~DriverBase() {}
};

#endif