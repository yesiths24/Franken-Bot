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
    while (state == MANUAL) {
        // TODO: read image data from ucam UART

        // TODO: send image data to phone


        sleep_ms(100);
    }

    // stop all motors
    set_drive_speeds(0,0);

    // TODO: return cam servo to centre

    return 0;
}

void run_auto(uint8_t mode, uint8_t target_id) {
    // powerup pi
    pi_powerup();

    // handshake w pi and send instructions
    pi_uart_setup();
    uart_putc(PI_UART_ID, mode);
    uart_putc(PI_UART_ID, target_id);


    // run autonomous loop as necessary
    // expect a shitload of interrupts (if pi5 uart has rx interrupt set up)
    while (state == AUTO) {
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
