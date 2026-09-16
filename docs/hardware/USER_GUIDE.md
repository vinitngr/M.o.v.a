# Hardware Framework — User Guide

## 1. What This Framework Does

The framework lets you connect supported hardware components to predefined sockets and identify them by name.

You normally do not need to think about physical GPIO numbers.

The basic idea is:

```text
Component
   ↓
Logical Socket
   ↓
Physical pins
```

Example:

```text
led_1
   ↓
GPIO Socket 1
   ↓
GPIO 4 + GPIO 5
```

---

# 2. Available Sockets

## GPIO sockets

Each GPIO socket has two signal lines.

```text
GPIO Socket 1
Signal 1 → GPIO 4
Signal 2 → GPIO 5

GPIO Socket 2
Signal 1 → GPIO 6
Signal 2 → GPIO 7

GPIO Socket 3
Signal 1 → GPIO 10
Signal 2 → GPIO 11
```

A one-signal component can use one signal.

A two-signal component can use both.

Because every GPIO socket has the same two-signal layout, supported GPIO components can be moved between compatible GPIO sockets.

---

## I2C sockets

```text
I2C Socket 1
SDA → GPIO 8
SCL → GPIO 9

I2C Socket 2
Not assigned

I2C Socket 3
Not assigned
```

I2C components should use I2C sockets.

---

# 3. Registering a Component

Component registration is done in:

```text
component_mapping.h
```

The format is:

```cpp
{
    "component_name",
    "component_interface",
    SOCKET
}
```

Example:

```cpp
{ "led_1", "led_adaptor", SOCKET_GPIO_1 }
```

This means:

```text
Component name:
led_1

Interface:
led_adaptor

Socket:
GPIO Socket 1
```

---

# 4. Adding Another Component

If the component type is already supported, add another entry.

Example:

```cpp
static const ComponentConfig COMPONENTS[] = {
    { "led_1", "led_adaptor", SOCKET_GPIO_1 },
    { "led_2", "led_adaptor", SOCKET_GPIO_3 },
};
```

Now:

```text
led_1 → GPIO Socket 1
led_2 → GPIO Socket 3
```

Each component needs a unique name.

---

# 5. Moving a Component

Suppose the configuration is:

```cpp
{ "led_1", "led_adaptor", SOCKET_GPIO_1 }
```

If you physically move the LED to GPIO Socket 3, change it to:

```cpp
{ "led_1", "led_adaptor", SOCKET_GPIO_3 }
```

You do not need to enter:

```text
GPIO 10
GPIO 11
```

The framework already knows that GPIO Socket 3 uses those pins.

---

# 6. Choosing a Socket

Choose the socket according to the component connection type.

### GPIO component

Use one of:

```text
SOCKET_GPIO_1
SOCKET_GPIO_2
SOCKET_GPIO_3
```

### I2C component

Use one of:

```text
SOCKET_I2C_1
SOCKET_I2C_2
SOCKET_I2C_3
```

The physical component must also actually be plugged into the selected socket.

---

# 7. Adding a Supported Component

If the framework already supports the component type, registration is simple.

Example:

```cpp
{ "camera_1", "camera_adaptor", SOCKET_GPIO_3 }
```

This says:

```text
camera_1
→ use camera_adaptor
→ connected to GPIO Socket 3
```

You do not need to describe its physical GPIO pins here.

---

# 8. Adding a Completely New Component Type

If the framework does not support a component type yet, a developer needs to add support for that type first.

After support exists, registering individual components follows the normal process:

```cpp
{ "component_1", "component_adaptor", SOCKET_GPIO_1 }
```

So:

```text
Developer
→ adds support for a new component type

User
→ registers/configures instances of supported types
```

---

# 9. Naming Components

Give every component a unique name.

Examples:

```text
led_1
led_2
camera_1
camera_2
ultrasonic_front
ultrasonic_rear
```

Avoid:

```text
led_1
led_1
```

The name identifies the specific component in the system.

---

# 10. Using a Component

Once registered, the component can be accessed by its configured name.

For example:

```text
led_1
```

can be used without the application needing to know that it ultimately connects to:

```text
GPIO 4
```

The same principle applies to sensors and other supported components.

---

# 11. Reading Sensor Data

Registering a sensor does not mean that it continuously sends data.

The application can request data when needed:

```text
Application
    ↓
ask component for data
    ↓
component
    ↓
return value
```

If continuous monitoring is required, the application can repeatedly request the value:

```text
read
 ↓
process
 ↓
read
 ↓
process
 ↓
...
```

The framework does not need to continuously read every registered component just because it exists.

---

# 12. Camera / Streaming Behaviour

A camera being registered does not automatically mean it is continuously capturing or streaming.

Conceptually:

```text
Camera registered
→ available to application

Camera started
→ captures/streams

Camera stopped
→ stops capturing/streaming
```

Similarly, stopping capture does not necessarily mean the camera hardware is electrically powered off. Low-power/sleep behaviour is a separate hardware feature.

---

# 13. Quick Registration Checklist

When adding a supported component:

```text
1. Choose a unique name.
2. Choose its registered interface.
3. Choose the correct logical socket.
4. Physically plug the component into that socket.
5. Add the entry to COMPONENTS[].
6. Build and run.
```

Example:

```cpp
{ "sensor_1", "sensor_adaptor", SOCKET_GPIO_3 }
```

---

# 14. Current Setup

Current component configuration:

```cpp
static const ComponentConfig COMPONENTS[] = {
    { "led_1",        "led_adaptor",        SOCKET_GPIO_1 },
    { "ultrasonic_1", "ultrasonic_adaptor", SOCKET_GPIO_2 },
};
```

Current socket mapping:

```text
GPIO
├── Socket 1 → GPIO 4, GPIO 5
├── Socket 2 → GPIO 6, GPIO 7
└── Socket 3 → GPIO 10, GPIO 11

I2C
├── Socket 1 → SDA GPIO 8, SCL GPIO 9
├── Socket 2 → not assigned
└── Socket 3 → not assigned
```

Current physical arrangement:

```text
led_1
└── GPIO Socket 1

ultrasonic_1
└── GPIO Socket 2
```

---

# 15. The Simple Rule

For normal configuration, think only about:

```text
WHO?
→ component name

HOW?
→ component interface

WHERE?
→ logical socket
```

Example:

```cpp
{ "led_1", "led_adaptor", SOCKET_GPIO_1 }
```

You should normally **not** need to think about:

```text
GPIO 4
GPIO 5
driver internals
low-level pin operations
```

Those belong to the framework's hardware layer.
