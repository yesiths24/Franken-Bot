package com.example.frankenbotapp;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public class DataPacket {
    private static final int COMMAND_SIZE = 5;
    private static final int MESSAGE_SIZE = 20;

    private String command;
    private String message;

    public DataPacket(String command, String message) {
        this.command = command;
        this.message = message;
    }

    public byte[] toBytes() {
        ByteBuffer buffer = ByteBuffer.allocate(COMMAND_SIZE + MESSAGE_SIZE);
        buffer.order(ByteOrder.LITTLE_ENDIAN); // Match C struct order

        // Convert command to fixed-size array
        byte[] commandBytes = command.getBytes(StandardCharsets.UTF_8);
        byte[] commandFixedSize = new byte[COMMAND_SIZE];
        Arrays.fill(commandFixedSize, (byte) 0);
        System.arraycopy(commandBytes, 0, commandFixedSize, 0,
                Math.min(commandBytes.length, COMMAND_SIZE));

        // Convert message to fixed-size array
        byte[] messageBytes = message.getBytes(StandardCharsets.UTF_8);
        byte[] messageFixedSize = new byte[MESSAGE_SIZE];
        Arrays.fill(messageFixedSize, (byte) 0);
        System.arraycopy(messageBytes, 0, messageFixedSize, 0,
                Math.min(messageBytes.length, MESSAGE_SIZE));

        buffer.put(commandFixedSize);  // Add command
        buffer.put(messageFixedSize);  // Add message

        return buffer.array();
    }
}
