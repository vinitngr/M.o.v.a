#include "motion_adaptor.h"

#include "adaptor_registry.h"
#include "i2c_socket.h"
#include "mpu6050_driver.h"

#include <math.h>


MotionAdaptor::MotionAdaptor(
    Mpu6050Driver* driver
)
    : _driver(driver) {
}


void MotionAdaptor::init() {
    _driver->init();
}


bool MotionAdaptor::getAcceleration(
    float& ax,
    float& ay,
    float& az
) {

    int16_t rax;
    int16_t ray;
    int16_t raz;

    int16_t gx;
    int16_t gy;
    int16_t gz;


    if (
        !_driver->readRaw(
            rax,
            ray,
            raz,
            gx,
            gy,
            gz
        )
    ) {
        return false;
    }


    ax = rax / 16384.0;
    ay = ray / 16384.0;
    az = raz / 16384.0;

    return true;
}


bool MotionAdaptor::isMoving(
    float threshold
) {

    float ax;
    float ay;
    float az;


    if (!getAcceleration(
        ax,
        ay,
        az
    )) {
        return false;
    }


    float magnitude =
        sqrt(
            ax * ax +
            ay * ay +
            az * az
        );


    return fabs(
        magnitude - 1.0
    ) > (threshold - 1.0);
}


// Self registration

static void* createMotionAdaptor(
    uint8_t socket
) {

    I2cSocket* i2cSocket =
        new I2cSocket(
            socket,
            0x68
        );

    Mpu6050Driver* driver =
        new Mpu6050Driver(i2cSocket);

    return new MotionAdaptor(driver);
}


static struct MotionAdaptorRegistration {

    MotionAdaptorRegistration() {

        AdaptorRegistry::instance().registerAdaptor(
            MotionAdaptor::name(),
            createMotionAdaptor
        );
    }

} motionAdaptorRegistration;