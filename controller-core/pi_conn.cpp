#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "hardware/irq.h"
#include "drive/drive.cpp"

int cmd_chars_recv;
uint8_t cmd[3];


void on_pi_uart_rx() {
    
    while (uart_is_readable(PI_UART_ID)) {
        uint8_t cmd_char = uart_getc(PI_UART_ID);
        cmd[cmd_chars_recv] = cmd_char;
        cmd_chars_recv++;
        if (cmd_chars_recv == 3) {
            if (cmd[0] == (uint8_t) 'D' && cmd[1] == (uint8_t) 'R') {
                switch (cmd[2]) {
                    case (uint8_t) 'F':
                        set_drive_speeds(AUTO_DRIVE_SPEED, AUTO_DRIVE_SPEED);
                        printf("drive forward\n");
                        break;
                    case (uint8_t) 'B':
                        set_drive_speeds(-AUTO_DRIVE_SPEED, -AUTO_DRIVE_SPEED);
                        printf("drive backward\n");
                        break;
                    case (uint8_t) 'L':
                        set_drive_speeds(-0.75*AUTO_DRIVE_SPEED, 0.75*AUTO_DRIVE_SPEED);
                        printf("turn left\n");
                        break;
                    case (uint8_t) 'R':
                        set_drive_speeds(0.75*AUTO_DRIVE_SPEED, -0.75*AUTO_DRIVE_SPEED);
                        printf("turn right\n");
                        break;
                    case (uint8_t) 'S':
                        set_drive_speeds(0,0);
                        printf("halt\n");
                        break;
                    default:
                        printf("invalid drive command, halting!\n");
                }
            } else if (cmd[0] == (uint8_t) 'M' && cmd[1] == (uint8_t) 'R' && cmd[2] == (uint8_t) 'S') {
                int8_t leftSpeedByte = uart_getc(PI_UART_ID);
                int8_t rightSpeedByte = uart_getc(PI_UART_ID);
                printf("motorset %d, %d\n", (int) leftSpeedByte, (int) rightSpeedByte);
                set_drive_speeds((int) leftSpeedByte, (int) rightSpeedByte);
            } else {
                printf("invalid drive command, halting!\n");
            }

            cmd_chars_recv = 0;


        }
    }
}

void pi_powerup()
{
    gpio_set_dir(PI_POWER_CTRL_PIN, GPIO_OUT);
    gpio_pull_down(PI_POWER_CTRL_PIN);
    sleep_ms(1000);
    gpio_set_dir(PI_POWER_CTRL_PIN, 0);

}

int pi_uart_setup()
{
    stdio_init_all();

    cmd_chars_recv = 0;

    // Set up our UART
    uart_init(PI_UART_ID, PI_UART_BAUD_RATE);
    // Set the TX and RX pins by using the function select on the GPIO
    // Set datasheet for more information on function select
    gpio_set_function(PI_UART_TX_PIN, UART_FUNCSEL_NUM(PI_UART_ID, PI_UART_TX_PIN));
    gpio_set_function(PI_UART_RX_PIN, UART_FUNCSEL_NUM(PI_UART_ID, PI_UART_RX_PIN));


    // Set UART flow control CTS/RTS, we don't want these, so turn them off
    uart_set_hw_flow(PI_UART_ID, false, false);

    // Set our data format
    uart_set_format(PI_UART_ID, PI_UART_DATA_BITS, PI_UART_STOP_BITS, PI_UART_PARITY);

    // Turn off FIFO's - we want to do this character by character
    uart_set_fifo_enabled(PI_UART_ID, false);
    
    int UART_IRQ = PI_UART_ID == uart0 ? UART0_IRQ : UART1_IRQ;
    irq_set_exclusive_handler(UART_IRQ, on_pi_uart_rx);
    irq_set_enabled(UART_IRQ, true);

    uart_set_irqs_enabled(PI_UART_ID, true, false);

}