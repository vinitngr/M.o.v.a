#include "component_mapping.h"
#include "component_registry.h"
#include "adaptor_registry.h"

#include "gpio_socket.h"

#include "led_driver.h"
#include "ultrasonic_driver.h"

#include "led_adaptor.h"
#include "ultrasonic_adaptor.h"

#include "hook_registry.h"
#include "distance_to_led_hook.h"
#include "timed_blink_hook.h"


// Hardware objects

GpioSocket ledSocket(
    SOCKET_GPIO_1
);

LedDriver ledDriver(
    &ledSocket
);

LedAdaptor ledAdaptor(
    &ledDriver
);


GpioSocket ultrasonicSocket(
    SOCKET_GPIO_2
);

UltrasonicDriver ultrasonicDriver(
    &ultrasonicSocket
);

UltrasonicAdaptor ultrasonicAdaptor(
    &ultrasonicDriver
);


// Registries

AdaptorRegistry adaptorRegistry;

ComponentRegistry componentRegistry(
    &adaptorRegistry
);


// Hooks

DistanceToLedHook distanceToLedHook(
    &ultrasonicAdaptor,
    &ledAdaptor
);

TimedBlinkHook timedBlinkHook(
    &ledAdaptor
);


HookRegistry hookRegistry;


void setup() {
    Serial.begin(115200);

    // Register available adaptors
    adaptorRegistry.registerAdaptor(
        "led_adaptor",
        &ledAdaptor
    );

    adaptorRegistry.registerAdaptor(
        "ultrasonic_adaptor",
        &ultrasonicAdaptor
    );

    componentRegistry.init();

    ledAdaptor.init();
    ultrasonicAdaptor.init();

    // Hooks
    hookRegistry.registerHook(
        &timedBlinkHook
    );

    // Disabled for the timed blink test.
    // hookRegistry.registerHook(
    //     &distanceToLedHook
    // );

    hookRegistry.initAll();
}


void loop() {
    hookRegistry.tickAll();

    delay(10);
}