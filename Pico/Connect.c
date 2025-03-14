#include <stdio.h>
#include <string.h>
#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"
#include "lwip/tcp.h"
#include "picow_tcp_server.c"

#define WIFI_SSID "PicoW_Hotspot"
#define WIFI_PASSWORD "12345678"

// Start Wi-Fi hotspot
void start_hotspot() {
    printf("Starting Wi-Fi Hotspot...\n");
    if (cyw43_arch_init()) {
        printf("Wi-Fi initialization failed!\n");
        return;
    }
    cyw43_arch_enable_ap_mode(WIFI_SSID, WIFI_PASSWORD, CYW43_AUTH_WPA2_AES_PSK);
    printf("Hotspot '%s' started!\n", WIFI_SSID);
}

int main() {
    stdio_init_all();
    initDrive();
    
    sleep_ms(5000);
    start_hotspot();

    while(1) {
        run_tcp_server();
    }
    printf("Shutting down\n");
    cyw43_arch_deinit();
    return 0;
}
