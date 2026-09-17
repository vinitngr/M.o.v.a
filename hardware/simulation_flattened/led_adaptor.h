#ifndef LED_ADAPTOR_H
#define LED_ADAPTOR_H

#include "led_driver.h"

class LedAdaptor {
public:

    static const char* name() {
        return "led_adaptor";
    }

    LedAdaptor(LedDriver* driver);

    void init();

    void on();
    void off();
    void toggle();

    void blink(unsigned long ms);
    void update();

private:

    LedDriver* _driver;

    bool _state;
    bool _blinking;
    unsigned long _blinkOffAt;
};

#endif