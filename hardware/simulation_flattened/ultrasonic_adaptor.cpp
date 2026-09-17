#include "ultrasonic_adaptor.h"

#include "adaptor_registry.h"
#include "gpio_socket.h"
#include "ultrasonic_driver.h"


UltrasonicAdaptor::UltrasonicAdaptor(
    UltrasonicDriver* driver
)
    : _driver(driver) {
}


void UltrasonicAdaptor::init() {
    _driver->init();
}


float UltrasonicAdaptor::getDistanceCm() {
    return _driver->getDistanceCm();
}


// Self registration

static void* createUltrasonicAdaptor(
    uint8_t socket
) {

    GpioSocket* gpioSocket =
        new GpioSocket(socket);

    UltrasonicDriver* driver =
        new UltrasonicDriver(gpioSocket);

    UltrasonicAdaptor* adaptor =
        new UltrasonicAdaptor(driver);

    adaptor->init();

    return adaptor;
}


static struct UltrasonicAdaptorRegistration {

    UltrasonicAdaptorRegistration() {

        AdaptorRegistry::instance().registerAdaptor(
            UltrasonicAdaptor::name(),
            createUltrasonicAdaptor
        );
    }

} ultrasonicAdaptorRegistration;