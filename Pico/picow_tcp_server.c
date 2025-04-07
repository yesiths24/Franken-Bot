#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"

#include "lwip/pbuf.h"
#include "lwip/tcp.h"

#include "packet.h"
#include "commands.c"
#include "example.c"

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
    TCP_SERVER_T *state = calloc(1, sizeof(TCP_SERVER_T));
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

// Send a "Hello" message to the client
err_t tcp_server_send_hello(void *arg, struct tcp_pcb *tpcb) {
    const char *message = "Hello from Pico W!\n";
    
    DEBUG_printf("Sending message to client: %s", message);
    cyw43_arch_lwip_check();
    
    err_t err = tcp_write(tpcb, message, strlen(message), TCP_WRITE_FLAG_COPY);
    if (err != ERR_OK) {
        DEBUG_printf("Failed to send message: %d\n", err);
        return tcp_server_result(arg, -1);
    }
    tcp_output(tpcb);  // Ensure data is flushed
    return ERR_OK;
}



static err_t tcp_server_recv(void *arg, struct tcp_pcb *tpcb, struct pbuf *p, err_t err) {
    if (!p) {
        return tcp_close(tpcb);
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

err_t send_image_routine(struct tcp_pcb *tpcb);

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
    return send_image_routine(client_pcb); // Send image data
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

void run_tcp_server(void) {
    TCP_SERVER_T *state = tcp_server_init();
    if (!state) {
        streaming = 2;
        return;
    }
    if (!tcp_server_open(state)) {
        streaming = 2;
        tcp_server_result(state, -1);
        return;
    }
    while (!state->complete) {
#if PICO_CYW43_ARCH_POLL
        cyw43_arch_poll();
        cyw43_arch_wait_for_work_until(make_timeout_time_ms(1000));
#else
        sleep_ms(1000);
#endif
    }
    streaming = 2; // Stop streaming
    free(state);
}

err_t tcp_server_send_image();
static int64_t stream_image_callback(alarm_id_t id, void *user_data) {
    // This function will be called every STREAM_INTERVAL_MS milliseconds

    if (streaming == 0) {
        printf("Streaming image data...\n");
        tcp_server_send_image(fake_jpeg_data, tpcb1); // Send the image data
        add_alarm_in_ms(STREAM_INTERVAL_MS, stream_image_callback, NULL, true);
        
    } else if (streaming == 1) {
        printf("Streaming is paused.\n");
        add_alarm_in_ms(STREAM_INTERVAL_MS, stream_image_callback, NULL, true);
    } else if (streaming == 2) {
        printf("Streaming is stopped.\n");
        return -1; // Stop the alarm
    }   

    return 0;  // Return 0 to indicate success
}

err_t send_image_routine(struct tcp_pcb *tpcb) {
    tpcb1 = tpcb; // Store the client PCB for sending images later
    add_alarm_in_ms(STREAM_INTERVAL_MS, stream_image_callback, NULL, true); // Start streaming images
    return ERR_OK;
}

err_t send_next_chunk(struct tcp_pcb *tpcb, uint8_t *img) {
    size_t remaining = IMAGE_SIZE - jpeg_offset;
    if (remaining == 0) return ERR_OK;

    size_t to_send = remaining > CHUNK_SIZE ? CHUNK_SIZE : remaining;

    err_t err = tcp_write(tpcb, &fake_jpeg_data[jpeg_offset], to_send, TCP_WRITE_FLAG_COPY);
    if (err != ERR_OK) {
        printf("Chunk send error: %d\n", err);
        return err;
    }

    jpeg_offset += to_send;
    return tcp_output(tpcb);  // Push it
}

err_t tcp_server_send_image(uint8_t *img, struct tcp_pcb *tpcb) {
    if (!tpcb) return ERR_VAL;

    // Send image size as 4-byte big-endian integer
    uint32_t size_be = htonl(IMAGE_SIZE);  // convert to network byte order
    err_t err = tcp_write(tpcb, &size_be, sizeof(size_be), TCP_WRITE_FLAG_COPY);
    if (err != ERR_OK) {
        printf("Failed to send image size: %d\n", err);
        return err;
    } if (err == ERR_CONN) {
        printf("Connection closed: %d\n", err);
        streaming = 2; // Stop streaming
        return err;
    }

    // Send the actual image data
    jpeg_offset = 0;
    while (jpeg_offset < IMAGE_SIZE) {
        send_next_chunk(tpcb, img);
        printf("%d", jpeg_offset);
    } 
    return ERR_OK;

    // Flush buffer
    return tcp_output(tpcb);
}
