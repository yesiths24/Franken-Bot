package com.example.frankenbotapp;

import androidx.appcompat.app.AppCompatActivity;
import androidx.media3.common.MediaItem;
import androidx.media3.common.Player;
import androidx.media3.exoplayer.ExoPlayer;
import androidx.media3.ui.PlayerView;

import android.content.pm.ActivityInfo;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.TextView;
import android.widget.Toast;

import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import io.github.controlwear.virtual.joystick.android.JoystickView;

public class ManualActivity extends AppCompatActivity {
    private final ExecutorService executorService = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private static final long MIN_SEND_INTERVAL_MS = 500; // Minimum 500ms between sends
    private long lastSentTime = 0; // Track last send time

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.manual_control);
        setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
        JoystickView joystick = (JoystickView) findViewById(R.id.joystick1);
        TextView textView1 = (TextView) findViewById(R.id.textView1);
        joystick.setOnMoveListener(new JoystickView.OnMoveListener() {
            @Override
            public void onMove(int angle, int strength) {
                textView1.setText("Angle: " + angle + "°" + "\nStrength: " + strength + "%");
                sendTcpPacket("Move", angle + "," + strength);
            }
        });

        PlayerView playerView = (PlayerView) findViewById(R.id.playerView1);
        Player player = new ExoPlayer.Builder(this).build();
        playerView.setPlayer(player);
        try {
            MediaItem mediaItem = MediaItem.fromUri("rtsp://192.168.1.69:8554/test");
            player.setMediaItem(mediaItem);
            player.prepare();
            player.play();
        } catch (Exception e) {
            e.printStackTrace();
            showToast("Error: " + e.getMessage());
        }
    }
    /**
     * Sends the joystick angle and strength to the TCP server (Pico W).
     */
    private void sendTcpPacket(String command, String message) {
        long currentTime = System.currentTimeMillis();

        if (currentTime - lastSentTime < MIN_SEND_INTERVAL_MS) {
            return; // Skip sending if not enough time has passed
        }

        lastSentTime = currentTime; // Update last send time

        executorService.execute(() -> {
            DataPacket dataPacket = new DataPacket(command, message);
            boolean isSent = TcpClient.getInstance().sendPacket(dataPacket.toBytes());
            if (!isSent) {
                mainHandler.post(() -> showToast("Failed to send data"));
            }
        });
    }

    private void showToast(String message) {
        runOnUiThread(() -> Toast.makeText(ManualActivity.this, message, Toast.LENGTH_LONG).show());
    }

}