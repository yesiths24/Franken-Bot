#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"

#include "lwip/pbuf.h"
#include "lwip/tcp.h"

#include <algorithm>

#include "packet.h"
#include "commands.c"
#include "example.c"
#include "video_C_JAS.cpp"

#define TCP_PORT 1234
#define DEBUG_printf printf
#define POLL_TIME_S 5
#define COMMAND_SIZE 5
#define MAX_MESSAGE_SIZE 256 // Optional, limit for safety
#define STREAM_INTERVAL_MS 1000
#define CHUNK_SIZE 512


#define IMAGE_SIZE (sizeof(fake_jpeg_data))

typedef struct TCP_SERVER_T_ {
    struct tcp_pcb *server_pcb;
    struct tcp_pcb *client_pcb;
    bool complete;
} TCP_SERVER_T;

struct tcp_pcb *tpcb1;
int streaming = 0;  // Flag to indicate if streaming is active//paused//stopped
static size_t jpeg_offset = 0;

static TCP_SERVER_T* tcp_server_init(void) {
    TCP_SERVER_T *state = (TCP_SERVER_T *)calloc(1, sizeof(TCP_SERVER_T));
    if (!state) {
        DEBUG_printf("Failed to allocate state\n");
        return NULL;
    }
    return state;
}

static err_t tcp_server_close(void *arg) {
    TCP_SERVER_T *state = (TCP_SERVER_T*)arg;
    err_t err = ERR_OK;
    if (state->client_pcb != NULL) {
        tcp_arg(state->client_pcb, NULL);
        tcp_poll(state->client_pcb, NULL, 0);
        tcp_sent(state->client_pcb, NULL);
        tcp_recv(state->client_pcb, NULL);
        tcp_err(state->client_pcb, NULL);
        err = tcp_close(state->client_pcb);
        if (err != ERR_OK) {
            DEBUG_printf("Close failed %d, calling abort\n", err);
            tcp_abort(state->client_pcb);
            err = ERR_ABRT;
        }
        state->client_pcb = NULL;
    }
    if (state->server_pcb) {
        tcp_arg(state->server_pcb, NULL);
        tcp_close(state->server_pcb);
        state->server_pcb = NULL;
    }
    return err;
}

static err_t tcp_server_result(void *arg, int status) {
    TCP_SERVER_T *state = (TCP_SERVER_T*)arg;
    if (status == 0) {
        DEBUG_printf("Test success\n");
    } else {
        DEBUG_printf("Test failed %d\n", status);
    }
    state->complete = true;
    return tcp_server_close(arg);
}




static err_t tcp_server_recv(void *arg, struct tcp_pcb *tpcb, struct pbuf *p, err_t err) {
    if (!p) {
        printf("Client disconnected\n");
        tcp_server_result(arg, 0);  // Or some status if needed
        return ERR_OK;
    }
    if (p->tot_len < COMMAND_SIZE) {
        // Not enough data to contain a full command
        pbuf_free(p);
        return ERR_OK;
    }
    

    char command[COMMAND_SIZE + 1] = {0};  // +1 for null-termination
    char message[MAX_MESSAGE_SIZE] = {0}; // Adjust based on expected limits

    // Copy command (first 5 bytes)
    pbuf_copy_partial(p, command, COMMAND_SIZE, 0);
    command[COMMAND_SIZE] = '\0';

    // Copy remaining data as message
    uint16_t message_len = p->tot_len - COMMAND_SIZE;
    if (message_len > 0) {
        pbuf_copy_partial(p, message, 
            message_len < MAX_MESSAGE_SIZE ? message_len : MAX_MESSAGE_SIZE - 1,
            COMMAND_SIZE);
        message[message_len < MAX_MESSAGE_SIZE ? message_len : MAX_MESSAGE_SIZE - 1] = '\0';
    }

    printf("Received Data: Command=%s, Message=%s\n", command, message);

    process_command(command, message);  // You’ll pass both as strings now

    pbuf_free(p);
    return ERR_OK;
}


static err_t tcp_server_accept(void *arg, struct tcp_pcb *client_pcb, err_t err) {
    TCP_SERVER_T *state = (TCP_SERVER_T*)arg;
    if (err != ERR_OK || client_pcb == NULL) {
        DEBUG_printf("Failure in accept\n");
        return ERR_VAL;
    }
    
    DEBUG_printf("Client connected\n");

    state->client_pcb = client_pcb;
    tcp_arg(client_pcb, state);
    tcp_recv(client_pcb, tcp_server_recv);
    tcp_err(client_pcb, NULL);

    // Send "Hello" message upon connection
    return ERR_OK; // Send image data
}

static bool tcp_server_open(void *arg) {
    TCP_SERVER_T *state = (TCP_SERVER_T*)arg;
    DEBUG_printf("Starting server on port %u\n", TCP_PORT);

    struct tcp_pcb *pcb = tcp_new_ip_type(IPADDR_TYPE_ANY);
    if (!pcb) {
        DEBUG_printf("Failed to create PCB\n");
        return false;
    }

    err_t err = tcp_bind(pcb, NULL, TCP_PORT);
    if (err) {
        DEBUG_printf("Failed to bind to port %u\n", TCP_PORT);
        return false;
    }

    state->server_pcb = tcp_listen_with_backlog(pcb, 1);
    if (!state->server_pcb) {
        DEBUG_printf("Failed to listen\n");
        tcp_close(pcb);
        return false;
    }

    tcp_arg(state->server_pcb, state);
    tcp_accept(state->server_pcb, tcp_server_accept);

    return true;
}

void send_image(TCP_SERVER_T *state, const std::vector<uint8_t>& image_data) {
    if (state->client_pcb == NULL) {
        printf("No client connected.\n");
        return;
    }

    uint32_t img_len = image_data.size();
    uint8_t len_bytes[4] = {
        (uint8_t)(img_len >> 24),
        (uint8_t)(img_len >> 16),
        (uint8_t)(img_len >> 8),
        (uint8_t)(img_len)
    };

    // Send 4-byte header first
    tcp_write(state->client_pcb, len_bytes, 4, TCP_WRITE_FLAG_COPY);
    tcp_output(state->client_pcb);

    // Then send image in chunks as before
    const uint8_t* data = image_data.data();
    size_t sent = 0;

    while (sent < img_len) {
        size_t space = tcp_sndbuf(state->client_pcb);
        size_t chunk = std::min((size_t)CHUNK_SIZE, image_data.size() - sent);

        if (chunk > space) {
            sleep_ms(10);
            continue;
        }

        err_t err = tcp_write(state->client_pcb, data + sent, chunk, TCP_WRITE_FLAG_COPY);
        if (err != ERR_OK) {
            printf("tcp_write failed: %d\n", err);
            return;
        }

        tcp_output(state->client_pcb);
        sent += chunk;
    }

    printf("Image sent successfully: %u bytes\n", img_len);
}


void stream(TCP_SERVER_T *state) {
    if (state->client_pcb == NULL) {
        return; // No active connection, don't stream
    }
    uart_init(uart0, 115200); // Or 921600 if stable
    gpio_set_function(0, GPIO_FUNC_UART); // TX
    gpio_set_function(1, GPIO_FUNC_UART); // RX

    init_cam();

    std::vector<uint8_t> image;
    if (capture_frame_once(image)) {
        printf("Sending image over TCP...\n");
        send_image(state, image);
        //print the image data to the console
        printf("Image data: ");
        for (size_t i = 0; i < image.size(); ++i) {
            printf("%02X ", image[i]);
        }
        printf("\n");
        printf("Done!\n");
    } else {
        printf("Capture failed.\n");
    }
    
    while (1) sleep_ms(1000);
}


void run_tcp_server(void) {
    TCP_SERVER_T *state = tcp_server_init();
    if (!state) {
        return;
    }
    if (!tcp_server_open(state)) {

        tcp_server_result(state, -1);
        return;
    }
    while (!state->complete) {
        stream(state);
#if PICO_CYW43_ARCH_POLL
        cyw43_arch_poll();
        cyw43_arch_wait_for_work_until(make_timeout_time_ms(1000));
#else
        sleep_ms(1000);
#endif
    }
    free(state);
}



