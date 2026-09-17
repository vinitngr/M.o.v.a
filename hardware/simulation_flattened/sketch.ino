#include "component_mapping.h"
#include "component_registry.h"
#include "adaptor_registry.h"

#include "hook_registry.h"
#include "distance_to_led_hook.h"

AdaptorRegistry& adaptorRegistry =
    AdaptorRegistry::instance();

ComponentRegistry componentRegistry(
    &adaptorRegistry
);

HookRegistry hookRegistry;

DistanceToLedHook distanceToLedHook(
    &componentRegistry
);

void setup() {
    Serial.begin(115200);

    componentRegistry.init();

    hookRegistry.registerHook(
        &distanceToLedHook
    );

    hookRegistry.initAll();
}

void loop() {
    hookRegistry.tickAll();

    delay(10);
}