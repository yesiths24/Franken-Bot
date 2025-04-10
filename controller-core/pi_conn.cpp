#include <stdio.h>
#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "hardware/irq.h"
#include "hwconfigs.h"
#include "drive/drive.cpp"

int cmd_chars_recv;
uint8_t cmd[3];


void on_pi_uart_rx() 
{
    
    while (uart_is_readable(PI_UART_ID)) {
        uint8_t cmd_char = uart_getc(PI_UART_ID);
        cmd[cmd_chars_recv] = cmd_char;
        cmd_chars_recv++;
        printf("Recv %d, count = %d\n", cmd_char, cmd_chars_recv);
        if (cmd[0] == (uint8_t) 'D') {
            if (cmd[1] == (uint8_t) 'R' && cmd_chars_recv > 1) {
                if (cmd_chars_recv > 2) {
                    switch (cmd[2]) {
                        case (uint8_t) 'F':
                            set_drive_speeds(AUTO_DRIVE_SPEED, AUTO_DRIVE_SPEED);
                            printf("drive forward\n");
                            cmd_chars_recv = 0;
                            cmd[0] = 0;
                            cmd[1] = 0;
                            cmd[2] = 0;
                            cmd[3] = 0;
                            cmd[4] = 0;
                            break;
                        case (uint8_t) 'B':
                            set_drive_speeds(-AUTO_DRIVE_SPEED, -AUTO_DRIVE_SPEED);
                            printf("drive backward\n");
                            cmd_chars_recv = 0;
                            cmd[0] = 0;
                            cmd[1] = 0;
                            cmd[2] = 0;
                            cmd[3] = 0;
                            cmd[4] = 0;
                            break;
                        case (uint8_t) 'L':
                            set_drive_speeds(-0.75*AUTO_DRIVE_SPEED, 0.75*AUTO_DRIVE_SPEED);
                            printf("turn left\n");
                            cmd_chars_recv = 0;
                            cmd[0] = 0;
                            cmd[1] = 0;
                            cmd[2] = 0;
                            cmd[3] = 0;
                            cmd[4] = 0;
                            break;
                        case (uint8_t) 'R':
                            set_drive_speeds(0.75*AUTO_DRIVE_SPEED, -0.75*AUTO_DRIVE_SPEED);
                            printf("turn right\n");
                            cmd_chars_recv = 0;
                            cmd[0] = 0;
                            cmd[1] = 0;
                            cmd[2] = 0;
                            cmd[3] = 0;
                            cmd[4] = 0;
                            break;
                        case (uint8_t) 'S':
                            set_drive_speeds(0,0);
                            printf("halt\n");
                            cmd_chars_recv = 0;
                            cmd[0] = 0;
                            cmd[1] = 0;
                            cmd[2] = 0;
                            cmd[3] = 0;
                            cmd[4] = 0;
                            break;
                        default:
                            printf("invalid drive command, halting!\n");
                            set_drive_speeds(0,0);
                            cmd_chars_recv = 0;
                            cmd[0] = 0;
                            cmd[1] = 0;
                            cmd[2] = 0;
                            cmd[3] = 0;
                            cmd[4] = 0;
                    }
                }
            
            } else if (cmd_chars_recv > 1) {
                cmd_chars_recv = 0;
                cmd[0] = 0;
                cmd[1] = 0;
                cmd[2] = 0;
                cmd[3] = 0;
                cmd[4] = 0;
            }
        } else if (cmd[0] == (uint8_t) 'M') {
            if (cmd_chars_recv > 1 && cmd[1] == (uint8_t) 'T') {
                if (cmd_chars_recv > 2 && cmd[2] == (uint8_t) 'S') {
                    if (cmd_chars_recv > 4) {
                        printf("motorset %f, %f\n", round((((float) cmd[3]) - 100) * AUTO_DRIVE_SPEED / 100), round((((float) cmd[4]) - 100) * AUTO_DRIVE_SPEED / 100));
                        set_drive_speeds(round((((float) cmd[3]) - 100) * AUTO_DRIVE_SPEED / 100), round((((float) cmd[4]) - 100) * AUTO_DRIVE_SPEED / 100));
                        cmd_chars_recv = 0;
                        cmd[0] = 0;
                        cmd[1] = 0;
                        cmd[2] = 0;
                        cmd[3] = 0;
                        cmd[4] = 0;
                    } else  if (cmd_chars_recv > 4) {
                        cmd_chars_recv = 0;
                        cmd[0] = 0;
                        cmd[1] = 0;
                        cmd[2] = 0;
                        cmd[3] = 0;
                        cmd[4] = 0;
                    }
        
                } else if (cmd_chars_recv > 2) {
                    cmd_chars_recv = 0;
                    cmd[0] = 0;
                    cmd[1] = 0;
                    cmd[2] = 0;
                    cmd[3] = 0;
                    cmd[4] = 0;
                }
            } else if (cmd_chars_recv > 1) {
                cmd_chars_recv = 0;
                cmd[0] = 0;
                cmd[1] = 0;
                cmd[2] = 0;
                cmd[3] = 0;
                cmd[4] = 0;
            }
        } else {
            cmd[0] = 0;
            cmd[1] = 0;
            cmd[2] = 0;
            cmd[3] = 0;
            cmd[4] = 0;
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

void pi_uart_setup()
{
    stdio_init_all();

    cmd_chars_recv = 0;

    // Set up our UART
    uart_init(PI_UART_ID, PI_UART_BAUD_RATE);
    // Set the TX and RX pins by using the function select on the GPIO
    // Set datasheet for more information on function select
    gpio_set_function(PI_UART_TX_PIN, UART_FUNCSEL_NUM(PI_UART_ID, PI_UART_TX_PIN));
    gpio_set_function(PI_UART_RX_PIN, UART_FUNCSEL_NUM(PI_UART_ID, PI_UART_RX_PIN));

    uint8_t buf[3];
    uart_read_blocking(PI_UART_ID, buf, 3);

    uart_puts(PI_UART_ID, "PHL");


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