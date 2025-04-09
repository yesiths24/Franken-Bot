#include <cstdio>
#include <cstdint>
#include <cmath>
#include <vector>

#include "pico/stdlib.h"
#include "hardware/uart.h"
#include "hardware/gpio.h"
#include "hardware/timer.h"
#include "pico/cyw43_arch.h"

// ------------------- CONFIG -------------------
#define UART_ID       uart1
// Adjust these pins to match your wiring:
#define PIN_UART_TX   4
#define PIN_UART_RX   5
#define BAUD_RATE     921600

//---------------------------------------------------------
// Helper: Convert a hex string like "AA 0D 00 00 00 00" to a byte array
//---------------------------------------------------------
static std::vector<uint8_t> hex_string_to_bytes(const char *hex_str) {
    std::vector<uint8_t> result;
    while (*hex_str) {
        if (*hex_str == ' ') {
            ++hex_str;
            continue;
        }
        unsigned int byteVal;
        sscanf(hex_str, "%2x", &byteVal);
        result.push_back((uint8_t)byteVal);
        hex_str += 2;
    }
    return result;
}

//---------------------------------------------------------
// Print a vector of bytes in hex
//---------------------------------------------------------
static void print_hex_data(const std::vector<uint8_t>& data) {
    if (data.empty()) {
        printf("(no data)\n");
        return;
    }
    for (auto b : data) {
        printf("%02X ", b);
    }
    printf("\n");
}

//---------------------------------------------------------
// UART helper functions
//---------------------------------------------------------
static void uart_write_blocking_hex(const uint8_t *data, size_t len) {
    uart_write_blocking(UART_ID, data, len);
}

static void uart_read_all(std::vector<uint8_t>& buffer) {
    while (uart_is_readable(UART_ID)) {
        buffer.push_back(uart_getc(UART_ID));
    }
}

// Reads exactly `num_bytes` from UART, or times out after `timeout_ms`.
// On success, appends those bytes to `buffer` and returns true.
// On timeout, returns false.
static bool uart_read_exact(std::vector<uint8_t>& buffer, size_t num_bytes, uint32_t timeout_ms) {
    absolute_time_t start_time = get_absolute_time();
    while (buffer.size() < num_bytes) {
        if (uart_is_readable(UART_ID)) {
            buffer.push_back(uart_getc(UART_ID));
        }
        uint32_t elapsed = to_ms_since_boot(get_absolute_time()) - to_ms_since_boot(start_time);
        if (elapsed > timeout_ms) {
            return false;
        }
    }
    return true;
}

//---------------------------------------------------------
// CAMERA INIT / SYNC
//---------------------------------------------------------
static void sync_cam() {
    // The sync command
    std::vector<uint8_t> txData = hex_string_to_bytes("AA 0D 00 00 00 00");
    print_hex_data(txData);
    float wait_ms = 5.0f;
    const int max_tries = 60;

    while (uart_is_readable(UART_ID)) {
        uart_getc(UART_ID);
    }

    for (int i = 0; i < max_tries; i++) {
        // Send SYNC
        uart_write_blocking_hex(txData.data(), txData.size());
        sleep_ms((uint32_t)wait_ms);
        wait_ms += 1.0f; // Slightly increase wait each iteration

        int addr = 0;
        int count = 0;
        // If the camera responds, break early
        while (uart_is_readable(UART_ID)) {
            uint8_t data[6];
            data[addr] = uart_getc(UART_ID);
            if (addr == 0 && data[0] == 170) {
                addr++;
            } else if (addr == 1 && data[1] == 14) {
                addr++;
            } else if (addr == 2 && data[2] == 13) {
                addr++;
            } else if (addr == 3) {
                addr++;
            } else if (addr == 4 && data[4] == 0) {
                addr++;
            } else if (addr == 5 && data[5] == 0) {
                break;
            }
        }
    }

    // Read whatever the camera responded so far
    std::vector<uint8_t> rxData(6);
    uart_read_all(rxData);
    // uart_read_blocking(UART_ID, rxData.data(), rxData.size());

    printf("SYNC ACK response (%d bytes): ", (int)rxData.size());
    print_hex_data(rxData);

    std::vector<uint8_t> rxDataSync(6);
    uart_read_all(rxDataSync);
    // uart_read_blocking(UART_ID, rxData.data(), rxData.size());

    printf("SYNC response (%d bytes): ", (int)rxDataSync.size());
    print_hex_data(rxDataSync);

    // Send ACK: "AA 0E 0D 00 00 00"
    std::vector<uint8_t> ack = hex_string_to_bytes("AA 0E 0D 00 00 00");
    uart_write_blocking_hex(ack.data(), ack.size());
    sleep_ms(100);

    // Optionally read any immediate response to the ACK
    std::vector<uint8_t> rxAck;
    uart_read_all(rxAck);
    if (!rxAck.empty()) {
        printf("ACK response (%d bytes): ", (int)rxAck.size());
        print_hex_data(rxAck);
    }
}

static int init_cam() {
    uart_init(uart1, BAUD_RATE); // Or 921600 if stable
    gpio_set_function(4, GPIO_FUNC_UART); // TX
    gpio_set_function(5, GPIO_FUNC_UART); // RX
    // 1) SYNC
    sync_cam();

    // 2) INITIAL JPEG ("AA 01 00 07 03 05")
    {
        std::vector<uint8_t> cmd = hex_string_to_bytes("AA 01 00 07 03 05");
        uart_write_blocking_hex(cmd.data(), cmd.size());
        sleep_ms(1000);

        // Read any response
        std::vector<uint8_t> rx;
        uart_read_all(rx);
        printf("Init response (%d bytes): ", (int)rx.size());
        print_hex_data(rx);
        if (rx.size() <= 0) {
            printf("No response from camera.\n");
            return -1;
        }
    }

    // 3) SET PACKAGE SIZE: 256 bytes ("AA 06 08 00 01 00")
    {
        std::vector<uint8_t> cmd = hex_string_to_bytes("AA 06 08 00 01 00");
        uart_write_blocking_hex(cmd.data(), cmd.size());
        sleep_ms(100);

        std::vector<uint8_t> rx;
        uart_read_all(rx);
        printf("Set package size response (%d bytes): ", (int)rx.size());
        print_hex_data(rx);
        if (rx.size() <= 0) {
            printf("No response from camera.\n");
            return -1;
        }
        else  {
            return 0;
        }
    }
}

//---------------------------------------------------------
// CAPTURE FUNCTION (read a single frame into RAM repeatedly)
// This version prints out ALL data read from the camera.
//---------------------------------------------------------
bool capture_frame_once(std::vector<uint8_t>& image_data) {
    printf("\nStarting image capture...");

    // Send GET PICTURE
    std::vector<uint8_t> cmd = hex_string_to_bytes("AA 04 05 00 00 00");
    uart_write_blocking_hex(cmd.data(), cmd.size());

    // Read 12-byte header
    std::vector<uint8_t> header(12);
    uart_read_blocking(UART_ID, header.data(), header.size());

    uint32_t length = header[9] + (header[10] << 8) + (header[11] << 16);
    printf("Image length: %u\n", length);

    // Fully release previous memory to avoid fragmentation
    printf("1");
    std::vector<uint8_t>().swap(image_data);
    printf("2");
    image_data.reserve(length);
    printf("3");

    uint32_t num_packets = (uint32_t)ceil(length / 250.0f);
    size_t offset = 0;

    for (uint32_t i = 0; i < num_packets; i++) {
        uint8_t prompt[6] = {0xAA, 0x0E, 0x00, 0x00, (uint8_t)(i & 0xFF), (uint8_t)(i >> 8)};
        uart_write_blocking(UART_ID, prompt, 6);

        if (i < num_packets - 1) {
            uint8_t packet[256];
            uart_read_blocking(UART_ID, packet, 256);
            for (int j = 4; j < 254 && offset < length; j++) {
                image_data.push_back(packet[j]);
                offset++;
            }
        } else {
            uint8_t header[4];
            uart_read_blocking(UART_ID, header, 4);
            uint16_t last_len = (header[3] << 8) | header[2];
            std::vector<uint8_t> last_packet(last_len);
            uart_read_blocking(UART_ID, last_packet.data(), last_len);

            for (int j = 0; j < last_len && offset < length; j++) {
                image_data.push_back(last_packet[j]);
                offset++;
            }

            uint8_t fin[6] = {0xAA, 0x0E, 0x00, 0x00, 0xF0, 0xF0};
            uart_write_blocking(UART_ID, fin, 6);
        }
    }

    printf("Image capture complete. Total bytes stored: %d\n", (int)image_data.size());
    return true;
}


void send_image_over_usb(const std::vector<uint8_t>& image_data) {
    printf("---START-IMAGE---\n"); // delimiter for the PC script
    for (uint8_t b : image_data) {
        putchar_raw(b);  // send raw byte over USB
    }
    printf("---END-IMAGE---\n");
}

/*

//---------------------------------------------------------
// MAIN
//---------------------------------------------------------
int main() {
    stdio_init_all();
    sleep_ms(5000); // Give USB time to initialize

    uart_init(uart0, 115200); // Or 921600 if stable
    gpio_set_function(0, GPIO_FUNC_UART); // TX
    gpio_set_function(1, GPIO_FUNC_UART); // RX

    init_cam();

    std::vector<uint8_t> image;
    if (capture_frame_once(image)) {
        printf("Sending image over USB...\n");
        send_image_over_usb(image);
        printf("Done!\n");
    } else {
        printf("Capture failed.\n");
    }

    while (1) sleep_ms(1000);
}*/