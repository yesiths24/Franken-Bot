#include <stdio.h>
#include <string.h>
#include "packet.h"
#include <math.h>
#include "drive.c"

void process_command(Data *data) {
    if (strcmp(data->command, "drv") == 0) {
        printf("Moving to %s\n", data->message);

        float left, right;
        
        sscanf(data->message, "%f,%f",&left, &right);
        
        setDriveSpeeds(left, right);

        

    } else if (strcmp(data->command, "Stop") == 0) {
        printf("Stopping\n");
    } else {
        printf("Unknown command\n");
    }
}