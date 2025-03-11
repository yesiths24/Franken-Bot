#ifndef PACKET_H
#define PACKET_H

#include <stdint.h>

#define COMMAND_SIZE 5
#define MESSAGE_SIZE 20

typedef struct __attribute__((packed)) {
    char command[COMMAND_SIZE];
    char message[MESSAGE_SIZE];
} Data;

#endif
