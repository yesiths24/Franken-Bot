#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "pico/stdlib.h"
#include "pico/cyw43_arch.h"

#include "lwip/pbuf.h"
#include "lwip/tcp.h"

#include <algorithm>
#include <stdexcept>
#include "pico/time.h"


#include "packet.h"
#include "commands.cpp"
#include "video_C_JAS.cpp"

#define TCP_PORT 1234
#define DEBUG_printf printf
#define POLL_TIME_S 5
#define COMMAND_SIZE 5
#define MAX_MESSAGE_SIZE 256 // Optional, limit for safety
#define STREAM_INTERVAL_MS 1000
#define CHUNK_SIZE 512

#define COMMAND_SIZE 5
#define MESSAGE_SIZE 10



#define TIME_DIFF_MS(start, end) ((absolute_time_diff_us(start, end)) / 1000)

bool init = false;
typedef struct TCP_SERVER_T_ {
    struct tcp_pcb *server_pcb;
    struct tcp_pcb *client_pcb;
    bool complete;
} TCP_SERVER_T;

struct tcp_pcb *tpcb1;
bool streaming = true;  // Flag to indicate if streaming is active//paused//stopped
static size_t jpeg_offset = 0;
bool ackReceived = false; // Flag to indicate if ACK was received

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
        ackReceived = false; // Reset the flag if client disconnected
        return ERR_OK;
    }
    if (p->tot_len < COMMAND_SIZE) {
        // Not enough data to contain a full command
        pbuf_free(p);
        return ERR_OK;
    }
    


    char command[COMMAND_SIZE + 1] = {0};  // null-terminated
    char message[MESSAGE_SIZE + 1] = {0};  // null-terminated

    if (p->tot_len < COMMAND_SIZE + MESSAGE_SIZE) {
        // Not enough bytes yet
        pbuf_free(p);
        return ERR_OK;
    }

    // Read full packet
    uint8_t buffer[COMMAND_SIZE + MESSAGE_SIZE];
    pbuf_copy_partial(p, buffer, COMMAND_SIZE + MESSAGE_SIZE, 0);

    memcpy(command, buffer, COMMAND_SIZE);
    memcpy(message, buffer + COMMAND_SIZE, MESSAGE_SIZE);

    // Optional: strip trailing 0s from message if needed


    printf("Received Data: Command=%s, Message=%s\n", command, message);
    if (strcmp(command, "ack") == 0) {
        ackReceived = true; // Set the flag to true when ACK is received
        printf("ACK received\n");

    }
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


/*********************************************************************
 *  capture_frame_and_stream()
 *  --------------------------
 *  Captures a single JPEG from the camera **and** pushes it out on
 *  the already‑connected TCP socket, packet by packet.
 *
 *  – Uses at most 256 bytes of RAM for buffering.
 *  – Returns true on success, false on any protocol/length error.
 *********************************************************************/
bool capture_frame_and_stream(TCP_SERVER_T *state)
{
    printf("capture_frame_and_stream()\n");
    if (state->client_pcb == nullptr) return false;   // no client

    /* ---------- 1. Ask the camera for a picture ---------- */
    static const uint8_t get_pic_cmd[] = {0xAA,0x04,0x05,0x00,0x00,0x00};
    uart_write_blocking(UART_ID, get_pic_cmd, sizeof(get_pic_cmd));
    printf("write ");

    /* ---------- 2. Read 12‑byte header ---------- */
    uint8_t hdr0[6];
    uart_read_blocking(UART_ID, hdr0, sizeof(hdr0));
    printf("hdr0: %02X %02X %02X %02X %02X %02X\n", hdr0[0], hdr0[1], hdr0[2], hdr0[3], hdr0[4], hdr0[5]);
    uint8_t hdr1[6];
    uart_read_blocking(UART_ID, hdr1, sizeof(hdr1));
    printf("hdr1: %02X %02X %02X %02X %02X %02X\n", hdr1[0], hdr1[1], hdr1[2], hdr1[3], hdr1[4], hdr1[5]);

    uint32_t length = hdr1[3] | (hdr1[4] << 8) | (hdr1[5] << 16);
    const uint32_t MAX_IMAGE_SIZE = 100000;           // sanity check
    if (length == 0 || length > MAX_IMAGE_SIZE) {
        printf("Invalid image length: %u\n", length);
        //return false;
    }
    printf("Image length: %u\n", length);

    /* 3.  Send the size to the client (big‑endian) --------------- */
    uint32_t be_len = htonl(length);                 // <arpa/inet.h>
    tcp_write(state->client_pcb, &be_len, 4, TCP_WRITE_FLAG_COPY);
    tcp_output(state->client_pcb);                   // push it out
    /* ---------- 4. Read every 250‑byte packet and forward ---------- */
    const uint32_t num_packets = (uint32_t)ceil(length / 250.0f);
    uint8_t uart_buf[256];            // 4‑byte camera header + 250 payload + 2 CRC

    for (uint32_t i = 0; i < num_packets; ++i)
    {
        /* 4.1  Ask for the i‑th packet */
        uint8_t prompt[6] = {0xAA, 0x0E, 0x00, 0x00,
                             uint8_t(i & 0xFF), uint8_t(i >> 8)};
        uart_write_blocking(UART_ID, prompt, sizeof(prompt));

        /* 4.2  Receive the packet */
        if (i < num_packets - 1) {
            uart_read_blocking(UART_ID, uart_buf, 256);
            // bytes 0‑3 = camera header, 4‑253 = 250 payload, 254‑255 = CRC
            tcp_write(state->client_pcb, uart_buf + 4, 250, TCP_WRITE_FLAG_COPY);
        }
        else {   // last packet has variable length
            uint8_t lp_hdr[4];
            uart_read_blocking(UART_ID, lp_hdr, 4);
            uint16_t last_len = (lp_hdr[3] << 8) | lp_hdr[2];

            // safety belt
            if (last_len > 250) last_len = 250;
            printf("here");
            if (uart_read_n_timeout(UART_ID, uart_buf, last_len, 500) == false) {
                printf("UART timeout\n");
                return false;
            }
            //uart_read_blocking(UART_ID, uart_buf, last_len);
            printf("there");
            if (uart_read_n_timeout(UART_ID, NULL, 2, 500) == false) {
                printf("UART timeout\n");
                return false;
            }
            //uart_read_blocking(UART_ID, NULL, 2);
            printf("where");
            tcp_write(state->client_pcb, uart_buf, last_len, TCP_WRITE_FLAG_COPY);

            // Tell camera we are done
            uint8_t fin[6] = {0xAA,0x0E,0x00,0x00,0xF0,0xF0};
            uart_write_blocking(UART_ID, fin, sizeof(fin));
        }

        /* 4.3  Push out pending data right away to keep the TCP window moving */
        tcp_output(state->client_pcb);
    }

    printf("Image capture + stream complete.\n");
    return true;
}

void stream(TCP_SERVER_T *state)
{
    if (!streaming) {
        printf("Streaming paused.\n");
        return;
    }
    printf("stream()\n");
    if (state->client_pcb == NULL) return;   // no client

    absolute_time_t t0 = get_absolute_time();

    // 1. Camera init (unchanged)
    if (!init) { 
        if (init_cam() < 0) {
            printf("Camera init failed.\n");
            streaming = false;
            return;
        }
        printf("Camera initialized.\n");
        init = true; 
        }

    // 2. Capture **and** stream in one go
    absolute_time_t t2 = get_absolute_time();
    bool ok = capture_frame_and_stream(state);
    absolute_time_t t3 = get_absolute_time();

    if (!ok) printf("Capture failed.\n");

    printf("[Timing] capture+TCP took %lld ms\n", TIME_DIFF_MS(t2, t3));
    printf("[Timing] Total stream() call time: %lld ms\n",
           TIME_DIFF_MS(t0, get_absolute_time()));
    ackReceived = false;
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
        //check if client disconnect
        if (state->client_pcb == NULL) {
            ackReceived = false; // Reset the flag if client disconnected
        } else if (ackReceived) {
            stream(state);
        } else {
            // Wait for ACK before streaming
            printf(".");
        }
        sleep_ms(10); // Polling interval
#if PICO_CYW43_ARCH_POLL
        cyw43_arch_poll();
        cyw43_arch_wait_for_work_until(make_timeout_time_ms(1000));
#else
        sleep_ms(1000);
#endif
    }
    free(state);
}



