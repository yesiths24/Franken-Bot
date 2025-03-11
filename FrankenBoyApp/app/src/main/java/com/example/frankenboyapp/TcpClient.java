package com.example.frankenboyapp;

import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;

public class TcpClient {
    private static TcpClient instance;
    private static final String SERVER_IP = "192.168.4.1"; // Change this to your server's IP
    private static final int SERVER_PORT = 1234; // Change this to your server's port
    private Socket socket;
    private OutputStream outputStream;
    private InputStream inputStream;

    private TcpClient() {
        // Private constructor to prevent instantiation
    }

    public static synchronized TcpClient getInstance() {
        if (instance == null) {
            instance = new TcpClient();
        }
        return instance;
    }

    public boolean connect() {
        if (socket != null && socket.isConnected()) {
            disconnect();
        }

        try {
            socket = new Socket();
            socket.connect(new InetSocketAddress(SERVER_IP, SERVER_PORT), 5000); // 5-second timeout
            outputStream = socket.getOutputStream();
            inputStream = socket.getInputStream();
            return true;
        } catch (IOException e) {
            e.printStackTrace();
            return false;
        }
    }

    public boolean sendPacket(byte[] packet) {
        try {
            if (outputStream != null) {
                outputStream.write(packet);
                outputStream.flush();
                return true;
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        return false;
    }


    public String receiveMessage() {
        try {
            if (inputStream != null) {
                byte[] buffer = new byte[1024];
                int bytesRead = inputStream.read(buffer);
                if (bytesRead > 0) {
                    return new String(buffer, 0, bytesRead).trim();
                }
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
        return null;
    }

    public void disconnect() {
        try {
            if (socket != null) {
                socket.close();
                socket = null;
            }
        } catch (IOException e) {
            e.printStackTrace();
        }
    }

    public boolean isConnected() {
        return socket != null && socket.isConnected();
    }
}
