package com.example.frankenbotapp;

import android.widget.TextView;

import java.io.ByteArrayOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.Socket;
import java.nio.ByteBuffer;

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

    public byte[] receiveImageBytes() throws IOException {
        if (inputStream == null) return null;

        // Step 1: Read 4-byte length
        byte[] lengthBuffer = new byte[4];
        int read = inputStream.read(lengthBuffer);
        if (read < 4) throw new IOException("Failed to read image length");

        int length = ((lengthBuffer[0] & 0xFF) << 24) |
                ((lengthBuffer[1] & 0xFF) << 16) |
                ((lengthBuffer[2] & 0xFF) << 8) |
                (lengthBuffer[3] & 0xFF);

        // Step 2: Read the image bytes
        byte[] imageData = new byte[length];
        int totalRead = 0;

        while (totalRead < length) {
            int bytesRead = inputStream.read(imageData, totalRead, length - totalRead);
            if (bytesRead == -1) throw new IOException("Stream closed early");
            totalRead += bytesRead;
        }

        return imageData;
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
