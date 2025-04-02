#!/usr/bin/python

# Simple script to convert list of hex bytes on STDIN to a binary file for testing
# needs to be in the format of "0x01 0x02 0x03" etc

import sys
output =  open("output.jpeg", 'wb')
input = open("image_test.txt","r")


for line in input:
    output.write(bytearray(int(i, 16) for i in line.strip().split(' ')))

output.close()
input.close()