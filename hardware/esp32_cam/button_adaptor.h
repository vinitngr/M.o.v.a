#ifndef BUTTON_ADAPTOR_H
#define BUTTON_ADAPTOR_H

#include "button_driver.h"

// Tactile push button -> latched 0/1.
// One physical press toggles the logical state (off->on, on->off).
// Debounced in software; hook polls via changed()/getState().
// Only sends on change (never polled by backend) to save power.
class ButtonAdaptor {
public:
    static const char* name() { return "button_adaptor"; }

    ButtonAdaptor(ButtonDriver* driver);
    void init();
    void update();          // call every tick; non-blocking
    bool getState() const;  // latched 0/1
    bool changed();         // true once per toggle; clears on read
    uint32_t seq() const;   // increments per toggle (for dedup)

private:
    ButtonDriver* _driver;
    bool _latched;
    bool _changed;
    uint32_t _seq;
    bool _lastRaw;
    bool _stablePressed;
    unsigned long _lastDebounceAt;
};

#endif
