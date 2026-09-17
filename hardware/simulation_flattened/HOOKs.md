# Creating a Hook

A hook connects two or more components (via their adaptors) with custom logic —
without going through a backend. Example: reading an ultrasonic sensor and
turning an LED on/off based on distance.

Every hook:
- Implements `HookBase` (`init()` + `tick()`)
- Fetches components by name from `ComponentRegistry`
- Gets registered once in `sketch.ino`
- Runs every loop cycle via `tickAll()`

---

## 1. Files to create

For a hook named `X`, create:

```
hooks/x_hook.h
hooks/x_hook.cpp
```

Naming: `<what_it_does>_hook.h/.cpp` (e.g. `distance_to_led_hook`, `motion_to_led_hook`).

---

## 2. Header template

```cpp
#ifndef X_HOOK_H
#define X_HOOK_H

#include "hook_base.h"

class XHook : public HookBase {
public:
    XHook(ComponentRegistry* registry) : HookBase(registry) {}

    void init() override;
    void tick() override;
};

#endif
```

---

## 3. Implementation template

```cpp
#include "x_hook.h"
#include "component_registry.h"

// include the adaptor types you need
#include "led_adaptor.h"
#include "ultrasonic_adaptor.h"

void XHook::init() {
    // one-time setup, if any. Often empty — components are already
    // init'd elsewhere before hooks run.
}

void XHook::tick() {
    auto sensor = _registry->use<UltrasonicAdaptor>(COMPONENT_ULTRASONIC_1);
    auto led = _registry->use<LedAdaptor>(COMPONENT_LED_1);

    if (!sensor || !led) return; // component missing/not registered — bail safely

    float distance = sensor->getDistanceCm();

    if (distance < 45) {
        led->on();
    } else {
        led->off();
    }
}
```

**Rules:**
- Always null-check every `use<T>()` result before using it. A missing/renamed
  component should never crash the loop.
- Use the `COMPONENT_*` name constants from `devices_config.h` — never hardcode
  raw strings like `"led_1"` inline.
- Keep `tick()` fast and non-blocking. No `delay()` inside a hook.

---

## 4. Running on a custom interval (optional)

By default `tick()` runs every loop cycle (currently every 100ms, set in
`sketch.ino`). If your hook should act less often, track it yourself:

```cpp
class XHook : public HookBase {
public:
    XHook(ComponentRegistry* registry) : HookBase(registry) {}
    void init() override;
    void tick() override;

private:
    unsigned long _lastRun = 0;
    unsigned long _intervalMs = 500;
};
```

```cpp
void XHook::tick() {
    if (millis() - _lastRun < _intervalMs) return;
    _lastRun = millis();

    // ...actual logic here
}
```

This keeps the global loop fast while letting each hook set its own pace.

---

## 5. Register the hook

In `sketch.ino`:

```cpp
#include "x_hook.h"

XHook xHook(&componentRegistry);

void setup() {
    // ...existing setup...
    hookRegistry.registerHook(&xHook);
    hookRegistry.initAll();
}
```

That's it — `hookRegistry.tickAll()` (already in `loop()`) will now call your
hook's `tick()` every cycle.

---

## Checklist for a new hook

- [ ] `hooks/<name>_hook.h` created, extends `HookBase`
- [ ] `hooks/<name>_hook.cpp` created, logic in `tick()`
- [ ] Used `_registry->use<T>(COMPONENT_*)`, not raw pin/socket access
- [ ] Null-checked every fetched component
- [ ] No `delay()` inside `tick()`
- [ ] Registered in `sketch.ino` via `hookRegistry.registerHook(...)`