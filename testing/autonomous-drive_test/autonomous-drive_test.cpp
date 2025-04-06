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


// void on_uart_rx() {
//     uint8_t cmd[5];
//     while (uart_is_readable(UART_ID)) {
//         uart_read_blocking(UART_ID, cmd, 4);
//         if (cmd[0] == (uint8_t) 'D' && cmd[1] == (uint8_t) 'R') {
//             switch (cmd[2]) {
//                 case (uint8_t) 'F':
//                     setDriveSpeeds(DRIVE_SPEED, DRIVE_SPEED);
//                     printf("drive forward\n");
//                     break;
//                 case (uint8_t) 'B':
//                     setDriveSpeeds(-DRIVE_SPEED, -DRIVE_SPEED);
//                     printf("drive backward\n");
//                     break;
//                 case (uint8_t) 'L':
//                     setDriveSpeeds(-DRIVE_SPEED, DRIVE_SPEED);
//                     printf("turn left\n");
//                     break;
//                 case (uint8_t) 'R':
//                     setDriveSpeeds(DRIVE_SPEED, -DRIVE_SPEED);
//                     printf("turn right\n");
//                     break;
//                 default:
//                     setDriveSpeeds(0,0);
//                     printf("halt\n");
//                     break;
//             }
//         }
//     }
// }


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

    while(1) {
        uint8_t cmd[5];
        cmd[0] = uart_getc(UART_ID);
        cmd[1] = uart_getc(UART_ID);
        cmd[2] = uart_getc(UART_ID);
        //cmd[3] = uart_getc(UART_ID);

        char state = 'S';

        printf("Recv: %c %c %c\n", cmd[0], cmd[1], cmd[2]);

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
                    setDriveSpeeds(-DRIVE_SPEED, DRIVE_SPEED);
                    printf("turn left\n");
                    break;
                case (uint8_t) 'R':
                    setDriveSpeeds(DRIVE_SPEED, -DRIVE_SPEED);
                    printf("turn right\n");
                    break;
                default:
                    setDriveSpeeds(0, 0);
                    printf("halt\n");
                    break;
            }
        } else {
            printf("halt\n");
            setDriveSpeeds(0,0);
        }
    }


    // // Set UART flow control CTS/RTS, we don't want these, so turn them off
    // uart_set_hw_flow(UART_ID, false, false);

    // // Set our data format
    // uart_set_format(UART_ID, DATA_BITS, STOP_BITS, PARITY);

    // // Turn off FIFO's - we want to do this character by character
    // uart_set_fifo_enabled(UART_ID, false);
    
    // int UART_IRQ = UART_ID == uart1 ? UART0_IRQ : UART1_IRQ;
    // irq_set_exclusive_handler(UART_IRQ, on_uart_rx);
    // irq_set_enabled(UART_IRQ, true);

    // uart_set_irqs_enabled(UART_ID, true, false);

    while (1) {
        continue;
    }
}
