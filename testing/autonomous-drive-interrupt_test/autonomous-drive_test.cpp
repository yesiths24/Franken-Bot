#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "hardware/irq.h"
#include "drive.cpp"


// UART defines
// By default the stdout UART is `uart0`, so we will use the second one
#define UART_ID uart1
#define BAUD_RATE 115200
#define DATA_BITS 8
#define STOP_BITS 1
#define PARITY    UART_PARITY_NONE

// Use pins 4 and 5 for UART1
// Pins can be changed, see the GPIO function select table in the datasheet for information on GPIO assignments
#define UART_TX_PIN 4
#define UART_RX_PIN 5

#define DRIVE_SPEED 35

int cmd_chars_recv;
uint8_t cmd[3];


void on_uart_rx() {
    
    while (uart_is_readable(UART_ID)) {
        uint8_t cmd_char = uart_getc(UART_ID);
        cmd[cmd_chars_recv] = cmd_char;
        cmd_chars_recv++;
        if (cmd_chars_recv == 3) {
            if (cmd[0] == (uint8_t) 'D' && cmd[1] == (uint8_t) 'R') {
                switch (cmd[2]) {
                    case (uint8_t) 'F':
                        setDriveSpeeds(DRIVE_SPEED, DRIVE_SPEED);
                        printf("drive forward\n");
                        break;
                    case (uint8_t) 'B':
                        setDriveSpeeds(-DRIVE_SPEED, -DRIVE_SPEED);
                        printf("drive backward\n");
                        break;
                    case (uint8_t) 'L':
                        setDriveSpeeds(-0.75*DRIVE_SPEED, 0.75*DRIVE_SPEED);
                        printf("turn left\n");
                        break;
                    case (uint8_t) 'R':
                        setDriveSpeeds(0.75*DRIVE_SPEED, -0.75*DRIVE_SPEED);
                        printf("turn right\n");
                        break;
                    case (uint8_t) 'S':
                        setDriveSpeeds(0,0);
                        printf("halt\n");
                        break;
                    default:
                        printf("invalid drive command, halting!\n");
                        setDriveSpeeds(0,0);
                }
            } else if (cmd[0] == (uint8_t) 'M' && cmd[1] == (uint8_t) 'R' && cmd[2] == (uint8_t) 'S') {
                int8_t leftSpeedByte = uart_getc(UART_ID);
                int8_t rightSpeedByte = uart_getc(UART_ID);
                printf("motorset %d, %d\n", (int) leftSpeedByte, (int) rightSpeedByte);
                setDriveSpeeds((int) leftSpeedByte, (int) rightSpeedByte);
            } else {
                printf("invalid drive command, halting!\n");
                setDriveSpeeds(0,0);
            }

            cmd_chars_recv = 0;


        }
    }
}


int main()
{
    stdio_init_all();
    initDrive();

    printf("Pico setting up...");
    cmd_chars_recv = 0;

    // Set up our UART
    uart_init(UART_ID, BAUD_RATE);
    // Set the TX and RX pins by using the function select on the GPIO
    // Set datasheet for more information on function select
    gpio_set_function(UART_TX_PIN, UART_FUNCSEL_NUM(UART_ID, UART_TX_PIN));
    gpio_set_function(UART_RX_PIN, UART_FUNCSEL_NUM(UART_ID, UART_RX_PIN));


    // Set UART flow control CTS/RTS, we don't want these, so turn them off
    uart_set_hw_flow(UART_ID, false, false);

    // Set our data format
    uart_set_format(UART_ID, DATA_BITS, STOP_BITS, PARITY);

    // Turn off FIFO's - we want to do this character by character
    uart_set_fifo_enabled(UART_ID, false);
    
    int UART_IRQ = UART_ID == uart0 ? UART0_IRQ : UART1_IRQ;
    irq_set_exclusive_handler(UART_IRQ, on_uart_rx);
    irq_set_enabled(UART_IRQ, true);

    uart_set_irqs_enabled(UART_ID, true, false);

    while (1) {
        tight_loop_contents();
    }
}
