#ifndef DRIVER_BASE_H
#define DRIVER_BASE_H

// Reused from simulation_flattened/driver_base.h (unchanged contract).
class DriverBase {
public:
    virtual void init() = 0;
    virtual ~DriverBase() {}
};

#endif
