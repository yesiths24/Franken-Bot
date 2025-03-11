package com.example.frankenboyapp;

import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Button;
import android.widget.Toast;

import androidx.appcompat.app.AppCompatActivity;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class ConnectActivity extends AppCompatActivity {
    private final ExecutorService executorService = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_connect);

        Button connectButton = findViewById(R.id.button1);
        connectButton.setOnClickListener(v -> {
            executorService.execute(() -> {
                boolean isConnected = TcpClient.getInstance().connect();
                mainHandler.post(() -> {
                    if (isConnected) {
                        startActivity(new Intent(ConnectActivity.this, ManualActivity.class));
                    } else {
                        showToast("Connection Failed");
                    }
                });
            });
        });
    }

    private void showToast(String message) {
        mainHandler.post(() -> Toast.makeText(ConnectActivity.this, message, Toast.LENGTH_LONG).show());
    }
}
