# Hardware & Component Framework — Admin / Developer Documentation

## 1. Purpose

This framework separates physical hardware wiring from component configuration.

```text
Physical MCU pins
        ↓
Logical sockets
        ↓
Component registration
        ↓
Component access
```

The important rule is:

**Component configuration uses logical socket IDs, not physical GPIO numbers.**

This allows a supported component to be moved between compatible sockets by changing its socket assignment.

---

## 2. Current Socket Layout

| Logical Socket | Type | Signal mapping |
|---|---|---|
| `SOCKET_I2C_1` | I2C | SDA GPIO 8, SCL GPIO 9 |
| `SOCKET_I2C_2` | I2C | Not assigned |
| `SOCKET_I2C_3` | I2C | Not assigned |
| `SOCKET_GPIO_1` | GPIO | Signal 1 → GPIO 4, Signal 2 → GPIO 5 |
| `SOCKET_GPIO_2` | GPIO | Signal 1 → GPIO 6, Signal 2 → GPIO 7 |
| `SOCKET_GPIO_3` | GPIO | Signal 1 → GPIO 10, Signal 2 → GPIO 11 |

### GPIO socket design

Every GPIO socket reserves two signal pins:

```text
┌─────────────────┐
│ VCC             │
│ GND             │
│ Signal 1        │
│ Signal 2        │
└─────────────────┘
```

A one-signal component may use only Signal 1.

A two-signal component may use Signal 1 and Signal 2.

Therefore all GPIO sockets have the same logical interface.

---

## 3. Socket Mapping

The physical mapping is defined in:

```text
socket_mapping.h
```

Current logical IDs:

```cpp
#define SOCKET_I2C_1   1
#define SOCKET_I2C_2   2
#define SOCKET_I2C_3   3

#define SOCKET_GPIO_1  4
#define SOCKET_GPIO_2  5
#define SOCKET_GPIO_3  6
```

Current physical mapping:

```text
SOCKET_GPIO_1 → GPIO 4, GPIO 5
SOCKET_GPIO_2 → GPIO 6, GPIO 7
SOCKET_GPIO_3 → GPIO 10, GPIO 11

SOCKET_I2C_1 → SDA GPIO 8, SCL GPIO 9
```

The component layer must not contain these physical GPIO numbers.

For example, use:

```cpp
SOCKET_GPIO_1
```

not:

```cpp
GPIO 4
GPIO 5
```

---

# 4. Component Registration

Component registration is defined in:

```text
component_mapping.h
```

The configuration structure is:

```cpp
struct ComponentConfig {
    const char* name;
    const char* adaptor;
    uint8_t socket;
};
```

Every registered component therefore has:

```text
name
adaptor
logical socket
```

Example:

```cpp
static const ComponentConfig COMPONENTS[] = {
    { "led_1",        "led_adaptor",        SOCKET_GPIO_1 },
    { "ultrasonic_1", "ultrasonic_adaptor", SOCKET_GPIO_2 },
};
```

---

## 5. Meaning of Each Field

### `name`

The unique identity of the component.

Example:

```text
led_1
```

This is the name application/backend code can use to refer to the component.

### `adaptor`

The registered interface associated with the component.

Example:

```text
led_adaptor
```

The component mapping does not need to contain a driver name.

### `socket`

The logical socket where the component is connected.

Example:

```cpp
SOCKET_GPIO_1
```

It does not contain the physical GPIO pins.

---

# 6. Registering Another Instance

If the component type is already supported, adding another instance is configuration.

Example:

```cpp
static const ComponentConfig COMPONENTS[] = {
    { "led_1", "led_adaptor", SOCKET_GPIO_1 },
    { "led_2", "led_adaptor", SOCKET_GPIO_3 },
};
```

This represents:

```text
led_1 → GPIO Socket 1
led_2 → GPIO Socket 3
```

The two instances have different names but can use the same component interface.

---

# 7. Moving a Component

Suppose:

```cpp
{ "led_1", "led_adaptor", SOCKET_GPIO_1 }
```

The physical LED is moved from GPIO Socket 1 to GPIO Socket 3.

Change the configuration to:

```cpp
{ "led_1", "led_adaptor", SOCKET_GPIO_3 }
```

Do not change the driver to GPIO 10 or GPIO 11.

The resolution remains:

```text
led_1
   ↓
SOCKET_GPIO_3
   ↓
Signal 1 → GPIO 10
Signal 2 → GPIO 11
```

This is the purpose of the socket abstraction.

---

# 8. Socket Compatibility

The selected socket must match the component's connection type.

### GPIO components

Use:

```text
SOCKET_GPIO_1
SOCKET_GPIO_2
SOCKET_GPIO_3
```

Every GPIO socket provides two signal channels.

### I2C components

Use:

```text
SOCKET_I2C_1
SOCKET_I2C_2
SOCKET_I2C_3
```

Currently only I2C Socket 1 has physical pins assigned.

---

# 9. Adding a New Supported Component

There are two cases.

## Case A — Component type already supported

Register an instance in `component_mapping.h`.

Example:

```cpp
{ "camera_1", "camera_adaptor", SOCKET_GPIO_3 }
```

assuming that the corresponding adaptor is already registered by the framework.

No new low-level driver is needed.

## Case B — Completely new component type

A developer must first implement support for the new component type.

The conceptual flow is:

```text
New component type
       ↓
Driver
       ↓
Adaptor
       ↓
Adaptor registration
       ↓
Component mapping
```

After that, users can register instances using the normal configuration format.

---

# 10. Adaptor Registration

The adaptor registry associates a configuration name with an adaptor implementation.

Conceptually:

```text
"led_adaptor"
      ↓
LED adaptor implementation

"ultrasonic_adaptor"
      ↓
Ultrasonic adaptor implementation
```

The component mapping refers to the string:

```cpp
"led_adaptor"
```

rather than directly storing driver information.

The registry is responsible for resolving the name to the appropriate registered interface.

---

# 11. Important Architecture Rule

Do not solve registration by creating a second file that simply hardcodes every component object.

The goal is:

```text
Configuration
    ↓
Registry
    ↓
Registered adaptor/factory
    ↓
Component instance
```

not:

```text
sketch.ino
    ↓
manually create every LED
    ↓
manually create every sensor
```

A true registry should make the configuration the source of component selection.

---

# 12. Initialization Lifecycle

The intended lifecycle is:

```text
1. Register available adaptors
2. Load component configuration
3. Resolve component names/interfaces
4. Create/connect required component instances
5. Initialize required components
6. Register application hooks
7. Run
```

Registration does not mean the component is continuously reading data.

It only makes the component available to the framework.

---

# 13. Reading Data

The registry should not continuously poll every component.

For an on-demand read:

```text
Application
    ↓
component accessor
    ↓
adaptor
    ↓
driver
    ↓
hardware
    ↓
value
```

For continuous operation, application logic can call the accessor repeatedly:

```text
loop
 ↓
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

This is important because registering a component should not automatically force every component to consume CPU time continuously.

A camera is a good example: registering it does not mean it must continuously capture frames. Continuous capture/streaming should be explicitly started.

---

# 14. Component Naming

Component names must be unique.

Good examples:

```text
led_1
led_2
camera_1
camera_2
ultrasonic_front
ultrasonic_rear
```

Bad:

```text
led_1
led_1
```

The component name is the runtime identity used to locate that particular component.

---

# 15. Physical Wiring vs Component Configuration

Physical wiring answers:

```text
Where is the component physically plugged in?
```

Component mapping answers:

```text
What component is assigned to that logical socket?
```

For example:

```text
Physical:
LED → GPIO Socket 1

Configuration:
led_1 → SOCKET_GPIO_1
```

The framework then resolves:

```text
led_1
  ↓
SOCKET_GPIO_1
  ↓
GPIO 4 + GPIO 5
```

This prevents application configuration from being coupled to board-specific GPIO numbers.

---

# 16. Developer Rules

When modifying the framework:

1. Keep physical pin information in `socket_mapping.h`.
2. Use logical socket IDs in component configuration.
3. Never put physical GPIO numbers into component mapping.
4. Keep component names unique.
5. Keep adaptor names stable and registered.
6. Validate socket compatibility.
7. Do not duplicate low-level component logic in application code.
8. Do not make the registry responsible for continuous polling.
9. Add support for a component type once; then allow multiple configured instances.
10. Moving a component between compatible sockets should normally require only changing its logical socket assignment.

---

# 17. Current Configuration

Current component mapping:

```cpp
static const ComponentConfig COMPONENTS[] = {
    { "led_1",        "led_adaptor",        SOCKET_GPIO_1 },
    { "ultrasonic_1", "ultrasonic_adaptor", SOCKET_GPIO_2 },
};
```

Current physical socket mapping:

```text
I2C
├── Socket 1 → SDA GPIO 8, SCL GPIO 9
├── Socket 2 → unassigned
└── Socket 3 → unassigned

GPIO
├── Socket 1 → Signal 1 GPIO 4, Signal 2 GPIO 5
├── Socket 2 → Signal 1 GPIO 6, Signal 2 GPIO 7
└── Socket 3 → Signal 1 GPIO 10, Signal 2 GPIO 11
```

Current configured instances:

```text
led_1
└── GPIO Socket 1

ultrasonic_1
└── GPIO Socket 2
```

---

# 18. Mental Model

Keep these three questions separate:

```text
SOCKET MAPPING
"Where are the physical pins?"

GPIO Socket 1
→ GPIO 4 + GPIO 5
```

```text
COMPONENT MAPPING
"What is connected where?"

led_1
→ GPIO Socket 1
```

```text
ADAPTOR REGISTRY
"Which interface handles this component?"

led_adaptor
→ registered adaptor implementation
```

The component mapping should therefore describe:

```text
component name
+
component interface
+
logical socket
```

It should not describe:

```text
physical GPIO pins
+
driver internals
+
hardware protocol details
```
