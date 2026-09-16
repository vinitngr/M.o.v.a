#ifndef LED_ADAPTOR_H
#define LED_ADAPTOR_H

#include "led_driver.h"

class LedAdaptor {
public:
    LedAdaptor(LedDriver* driver);
    void init();
    void on();
    void off();
    void toggle();
    void blink(unsigned long ms); // turns on, auto-off after ms
    void update(); // call every loop() to handle blink timing

private:
    LedDriver* _driver;
    bool _state;
    bool _blinking;
    unsigned long _blinkOffAt;
};

#endif