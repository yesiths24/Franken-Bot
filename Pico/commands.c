#include <stdio.h>
#include <string.h>
#include "packet.h"
#include <math.h>
#include "drive.c"

void process_command(char *command, char *message) {
    if (strcmp(command, "drv") == 0) {

        float left, right;
        
        sscanf(message, "%f,%f",&left, &right);
        
        setDriveSpeeds(left, right);

        

    } else if (strcmp(command, "stop") == 0) {
        printf("Stopping\n");
    } else {
        printf("Unknown command\n");
    }
}