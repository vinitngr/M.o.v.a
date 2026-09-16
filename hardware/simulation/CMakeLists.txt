idf_component_register(
    SRCS
        "sketch.ino"

        "sockets/gpio_socket.cpp"
        "sockets/i2c_socket.cpp"

        "drivers/led_driver.cpp"
        "drivers/mpu6050_driver.cpp"
        "drivers/ultrasonic_driver.cpp"

        "adaptors/led_adaptor.cpp"
        "adaptors/motion_adaptor.cpp"
        "adaptors/ultrasonic_adaptor.cpp"

        "hooks/hook_registry.cpp"
        "hooks/motion_to_led_hook.cpp"
        "hooks/distance_to_led_hook.cpp"
        "hooks/timed_blink_hook.cpp"

    INCLUDE_DIRS
        "."
        "sockets"
        "drivers"
        "adaptors"
        "hooks"
)