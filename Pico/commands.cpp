#include <stdio.h>
#include <string.h>
#include <math.h>
#include "packet.h"
#include "drive.cpp"
#include "lwip/tcp.h"

volatile int mode = 0; // 0 = manual, 1 = auto

void start_mode(int mode) {
    switch (mode) {
        case 0:
            printf("Starting manual mode\n");
            break;
        case 1:
            printf("Starting auto mode\n");
            break;
        case 2:
            printf("Starting track mode\n");
            break;
        default:
            printf("Unknown mode: %d\n", mode);
            break;
    }
}
/* -------------------------------------------------------------
 *  Command dispatcher
 * ------------------------------------------------------------*/
void process_command(const char *command, const char *message)
{
    /* --------------- drive ---------------- */
    if (strcmp(command, "drv") == 0 && mode == 0) {
        float left, right;
        if (sscanf(message, "%f,%f", &left, &right) == 2) {
            set_drive_speeds(left, right);
        }
        return;
    }

    /* --------------- stop ---------------- */
    if (strcmp(command, "stop") == 0 && mode == 0) {
        set_drive_speeds(0, 0);
        return;
    }

    /* --------------- mode ---------------- */
    if (strcmp(command, "mode") == 0) {

        if (strcmp(message, "manual") == 0) {
            /* switch to manual –‑ whatever that means for your robot */
            printf("Mode set to MANUAL\n");
            /* ... additional logic here ... */
            mode = 0; // Set mode to manual
            return;
        }

        if (strcmp(message, "tag") == 0) {
            /* switch to auto */
            printf("Mode set to tag\n");
            /* ... additional logic here ... */
            mode = 1; // Set mode to auto
            return;
        }

        if (strcmp(message, "track") == 0) {
            /* switch to auto */
            printf("Mode set to TRACK\n");
            /* ... additional logic here ... */
            mode = 2; // Set mode to auto
            return;
        }

        /* unknown mode payload */
        printf("Unknown mode: %s\n", message);
        start_mode(mode);
        return;
    }

    /* --------------- unknown command ---------------- */
    printf("Unknown command: %s\n", command);
}

// Runs on second core
void core1_entry() {
    while(true) {
        if (mode == 1) {
            printf("Running in auto mode\n");
        } else if (mode == 2) {
            printf("Running in track mode\n");
        } else {
            //printf("Running in manual mode\n");
        }
        sleep_ms(1000); // Sleep for 1 second
    }
}