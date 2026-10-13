#include "button_adaptor.h"
#include "adaptor_registry.h"
#include "dio_socket.h"
#include "button_driver.h"

static const unsigned long DEBOUNCE_MS = 50;

ButtonAdaptor::ButtonAdaptor(ButtonDriver* driver)
    : _driver(driver), _latched(false), _changed(false),
      _seq(0), _lastRaw(false), _stablePressed(false), _lastDebounceAt(0) {
}

void ButtonAdaptor::init() {
    _driver->init();
    _lastRaw = _driver->isPressed();
}

void ButtonAdaptor::update() {
    bool raw = _driver->isPressed();
    unsigned long now = millis();
    if (raw != _lastRaw) {
        _lastDebounceAt = now;
        _lastRaw = raw;
    }
    // Stable press edge (debounced active-low -> pressed==true):
    // toggle only on a new press, not on release or held-down.
    if ((now - _lastDebounceAt) >= DEBOUNCE_MS) {
        if (raw && !_stablePressed) {
            _stablePressed = true;
            _latched = !_latched;
            _changed = true;
            _seq++;
        } else if (!raw) {
            _stablePressed = false;
        }
    }
}

bool ButtonAdaptor::getState() const {
    return _latched;
}

bool ButtonAdaptor::changed() {
    if (_changed) {
        _changed = false;
        return true;
    }
    return false;
}

uint32_t ButtonAdaptor::seq() const {
    return _seq;
}

// Self registration (same pattern as simulation_flattened led_adaptor.cpp).
static void* createButtonAdaptor(uint8_t socket) {
    DioSocket* dio = new DioSocket(socket);
    ButtonDriver* driver = new ButtonDriver(dio);
    ButtonAdaptor* adaptor = new ButtonAdaptor(driver);
    adaptor->init();
    return adaptor;
}

static struct ButtonAdaptorRegistration {
    ButtonAdaptorRegistration() {
        AdaptorRegistry::instance().registerAdaptor(
            ButtonAdaptor::name(), createButtonAdaptor);
    }
} buttonAdaptorRegistration;
