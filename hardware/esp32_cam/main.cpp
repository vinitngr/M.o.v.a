#include <Arduino.h>
#include "adaptor_registry.h"
#include "component_registry.h"
#include "hook_registry.h"
#include "camera_driver.h"
#include "serial_test_hook.h"

AdaptorRegistry& adaptorRegistry = AdaptorRegistry::instance();
ComponentRegistry componentRegistry(&adaptorRegistry);
HookRegistry hookRegistry;
SerialTestHook serialTestHook(&componentRegistry);

void setup() {
    Serial.begin(115200);
    delay(200);

    componentRegistry.init();

    hookRegistry.registerHook(&serialTestHook);
    hookRegistry.initAll();

    Serial.println("[main] esp32_cam core ready");
    Serial.println("[main] pins: stream_btn=GPIO13 ai_btn=GPIO14 led=GPIO2");
    Serial.print("[main] camera mode: ");
#if CAMERA_SIMULATE
    Serial.println("SIMULATED");
#else
    Serial.println("REAL");
#endif
}

void loop() {
    hookRegistry.tickAll();
    delay(10);
}
