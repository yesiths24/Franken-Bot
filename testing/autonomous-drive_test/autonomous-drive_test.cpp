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

int main()
{
    stdio_init_all();
    initDrive();

    printf("Pico setting up...");

    // Set up our UART
    uart_init(UART_ID, BAUD_RATE);
    // Set the TX and RX pins by using the function select on the GPIO
    // Set datasheet for more information on function select
    gpio_set_function(UART_TX_PIN, GPIO_FUNC_UART);
    gpio_set_function(UART_RX_PIN, GPIO_FUNC_UART);

    while (uart_is_readable(UART_ID)) {
        uart_getc(UART_ID);
    }

    uint8_t cmd_chr;
    bool valid_cmd;

    while(1) {
        valid_cmd = 0;

        cmd_chr = uart_getc(UART_ID);
        if (cmd_chr == (uint8_t) 'D') {
            cmd_chr = uart_getc(UART_ID);
            if (cmd_chr == (uint8_t) 'R') {
                cmd_chr = uart_getc(UART_ID);
                switch (cmd_chr) {
                    case (uint8_t) 'F':
                        //setDriveSpeeds(DRIVE_SPEED, DRIVE_SPEED);
                        printf("drive forward\n");
                        valid_cmd = 1;
                        break;
                    case (uint8_t) 'B':
                        //setDriveSpeeds(-DRIVE_SPEED, -DRIVE_SPEED);
                        printf("drive backward\n");
                        valid_cmd = 1;
                        break;
                    case (uint8_t) 'L':
                        // setDriveSpeeds(-DRIVE_SPEED, DRIVE_SPEED);
                        printf("drive left\n");
                        valid_cmd = 1;
                        break;
                    case (uint8_t) 'R':
                        // setDriveSpeeds(DRIVE_SPEED, -DRIVE_SPEED);
                        printf("drive right\n");
                        valid_cmd = 1;
                        break;
                    case (uint8_t) 'S':
                        // setDriveSpeeds(0, 0);
                        printf("drive stop\n");
                        valid_cmd = 1;
                        break;
                }
            }
        } else if (cmd_chr == (uint8_t) 'M') {
            cmd_chr = uart_getc(UART_ID);
            if (cmd_chr == (uint8_t) 'R') {
                cmd_chr = uart_getc(UART_ID);
                if (cmd_chr == (uint8_t) 'S') {
                    int8_t leftSpeedByte = uart_getc(UART_ID);
                    int8_t rightSpeedByte = uart_getc(UART_ID);
                    valid_cmd = 1;
                    // setDriveSpeeds((float) leftSpeedByte, (float) rightSpeedByte);
                }
            }
        }

        if (!valid_cmd) {
            setDriveSpeeds(0,0);
            printf("invalid command: stopping!\n");
        }
        
        
    }

    while (1) {
        continue;
    }
}
