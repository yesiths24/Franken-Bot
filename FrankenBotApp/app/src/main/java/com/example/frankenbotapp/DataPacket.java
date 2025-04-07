package com.example.frankenbotapp;

import com.example.frankenbotapp.TcpClient;

import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

public class DataPacket {
    private static final int COMMAND_SIZE = 5;
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

        ByteBuffer buffer = ByteBuffer.allocate(COMMAND_SIZE + messageBytes.length);
        buffer.put(commandFixed);
        buffer.put(messageBytes);

        return buffer.array();
    }

    public static DataPacket fromBytes(byte[] data) {
        ByteBuffer buffer = ByteBuffer.wrap(data);
        buffer.order(ByteOrder.LITTLE_ENDIAN);

        int commandLength = buffer.getInt();

        byte[] commandBytes = new byte[commandLength];
        buffer.get(commandBytes);
        String command = new String(commandBytes, StandardCharsets.UTF_8);

        byte[] messageBytes = new byte[data.length - 4 - commandLength];
        buffer.get(messageBytes);
        String message = new String(messageBytes, StandardCharsets.UTF_8);

        return new DataPacket(command, message);
    }

}
