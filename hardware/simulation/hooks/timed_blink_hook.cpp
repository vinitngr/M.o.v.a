#include "timed_blink_hook.h"

TimedBlinkHook::TimedBlinkHook(LedAdaptor* led)
    : _led(led),
      _startTime(0),
      _lastToggle(0),
      _interval(1000),
      _started(false),
      _running(false) {}

void TimedBlinkHook::init() {
    _startTime = millis();
    _lastToggle = _startTime;
    _interval = 1000;

    _started = false;
    _running = false;

    _led->off();

    Serial.println("[TimedBlink] Initialized");
}

void TimedBlinkHook::tick() {
    unsigned long now = millis();
    unsigned long elapsed = now - _startTime;

    if (!_started && elapsed >= 2000) {
        _started = true;
        _running = true;
        _lastToggle = now;
        _interval = 1000;

        _led->on();

        Serial.println("[TimedBlink] Started - LED ON");
        return;
    }

    if (!_running) return;

    if (elapsed >= 50000) {
        _running = false;
        _led->off();

        Serial.println("[TimedBlink] Stopped - LED OFF");
        return;
    }

    if (now - _lastToggle >= _interval) {
        _lastToggle = now;

        _led->toggle();

        Serial.print("[TimedBlink] Toggle at ");
        Serial.print(elapsed);
        Serial.print(" ms, next interval = ");
        Serial.print(_interval * 2);
        Serial.println(" ms");

        _interval *= 2;
    }
}