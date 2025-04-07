#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/i2c.h"
#include "pico/cyw43_arch.h"
#include "hardware/uart.h"
#include "drive/drive.cpp"
#include "hwconfigs.h"
#include "pi_conn.cpp"

enum control_state {MANUAL, AUTO};
control_state state;


void init_robot() {
    init_drive();
    state = MANUAL;
}

int run_manual() {
    // stop all motors
    set_drive_speeds(0,0);

    // TODO: initialize ucam

    // run manual control loop
    // this will probably be interrupted a lot
    //  because all the manual control inputs are wifi commands
    while (state = MANUAL) {
        // TODO: read image data from ucam UART

        // TODO: send image data to phone


        sleep_ms(100);
    }

    // stop all motors
    set_drive_speeds(0,0);

    // TODO: return cam servo to centre

    return 0;
}

int run_auto() {
    // wake up pi

    // handshake w pi and send instructions

    // set up rx interrupt on pi UART? or already set up?
    //  is the pi5 likely to send gibberish during startup?
    //  also, is the interrupt practical here? It'll have to
    //      manage a lot of image data but also there's not
    //      actually much else going on

    // run autonomous loop as necessary
    // expect a shitload of interrupts (if pi5 uart has rx interrupt set up)
    while (state = AUTO) {
        sleep_ms(100);
    }

    // stop all motors

    // send shutdown command to pi5


}

int main() {
    stdio_init_all();
    init_robot();


    while (true) {
        switch (state) {
            MANUAL:
                run_manual();
                break;
            AUTO:
                run_auto();
                break;
        }
        tight_loop_contents();
    }
}
