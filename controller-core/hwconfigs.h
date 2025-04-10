// Pin assignments and config values for the Franken-Bot

// Streaming camera UART
#define CAM_UART_ID uart0
#define CAM_BAUD_RATE 115200

// RPi5 UART
#define PI_UART_ID uart1
#define PI_UART_TX_PIN 4
#define PI_UART_RX_PIN 5
#define PI_UART_BAUD_RATE 115200
#define PI_UART_DATA_BITS 8
#define PI_UART_STOP_BITS 1
#define PI_UART_PARITY    UART_PARITY_NONE

// RPi5 J2+ Header (power on/off)
#define PI_POWER_CTRL_PIN 14

// Autonomous drive properties
#define AUTO_DRIVE_SPEED 30

// drive system gpio/pwm config
// A is LEFT motor, B is RIGHT motor
#define DRV_PIN_STBY 22
#define DRV_PIN_B1 17
#define DRV_PIN_B2 16
#define DRV_PIN_A1 18
#define DRV_PIN_A2 19
#define DRV_PIN_PWMB 20
#define DRV_PIN_PWMA 21
#define DRV_PWMA_MAX 15000
#define DRV_PWMA_MIN 0
#define DRV_PWMB_MAX 15000
#define DRV_PWMB_MIN 0