#include <stdio.h>
#include <string.h>
#include "packet.h"
#include <math.h>
#include "drive.c"

void process_command(Data *data) {
    if (strcmp(data->command, "Move") == 0) {
        printf("Moving to %s\n", data->message);

        int angle, power;
        
        sscanf(data->message, "%d,%d", angle, power);
        
        moveAngleSpeed(angle, power);

        

    } else if (strcmp(data->command, "Stop") == 0) {
        printf("Stopping\n");
    } else {
        printf("Unknown command\n");
    }
}