package com.example.frankenbotapp;

import com.example.frankenbotapp.TcpClient;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public class DataPacket {
    private static final int COMMAND_SIZE = 5;
    private static final int MESSAGE_SIZE = 10; // example
    private String command;
    private String message;

    public DataPacket(String command, String message) {
        this.command = command;
        this.message = message;
    }


    public byte[] toBytes() {
        byte[] commandBytes = command.getBytes(StandardCharsets.UTF_8);
        byte[] commandFixed = new byte[COMMAND_SIZE];
        Arrays.fill(commandFixed, (byte) 0);
        System.arraycopy(commandBytes, 0, commandFixed, 0, Math.min(commandBytes.length, COMMAND_SIZE));

        byte[] messageBytes = message.getBytes(StandardCharsets.UTF_8);
        byte[] messageFixed = new byte[MESSAGE_SIZE];
        Arrays.fill(messageFixed, (byte) 0);
        System.arraycopy(messageBytes, 0, messageFixed, 0, Math.min(messageBytes.length, MESSAGE_SIZE));

        ByteBuffer buffer = ByteBuffer.allocate(MESSAGE_SIZE + COMMAND_SIZE);
        buffer.put(commandFixed);
        buffer.put(messageFixed);

        return buffer.array();
    }


}
