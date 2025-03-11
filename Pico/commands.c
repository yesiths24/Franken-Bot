#include <stdio.h>
#include <string.h>
#include "packet.h"

void process_command(Data *data) {
    if (strcmp(data->command, "Move") == 0) {
        printf("Moving to %s\n", data->message);
    } else if (strcmp(data->command, "Stop") == 0) {
        printf("Stopping\n");
    } else {
        printf("Unknown command\n");
    }
}