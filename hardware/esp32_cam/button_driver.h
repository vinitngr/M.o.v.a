#ifndef BUTTON_DRIVER_H
#define BUTTON_DRIVER_H

#include "dio_socket.h"

// Raw tactile push button: active-LOW with internal pull-up.
// Driver only does pin IO; toggle/debounce lives in the adaptor.
class ButtonDriver {
public:
    ButtonDriver(DioSocket* socket);
    void init();
    bool isPressed(); // true while physically held down

private:
    DioSocket* _socket;
};

#endif
