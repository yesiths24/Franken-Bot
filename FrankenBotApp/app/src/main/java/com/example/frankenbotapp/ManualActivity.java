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
import android.widget.SeekBar;
import android.widget.TextView;
import android.widget.Toast;

import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import io.github.controlwear.virtual.joystick.android.JoystickView;

public class ManualActivity extends AppCompatActivity {
    private final ExecutorService executorService = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private volatile int leftjoystickStrength = 0;
    private volatile int rightjoystickStrength = 0;
    private volatile boolean isSending = true;
    private volatile boolean isStopped = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.manual_control);
        //setRequestedOrientation(ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE);
//        SeekBar leftStick = (SeekBar) findViewById(R.id.seekBar1);
//        SeekBar rightStick = (SeekBar) findViewById(R.id.seekBar2);
        JoystickView leftStick = (JoystickView) findViewById(R.id.joystick1);
        JoystickView rightStick = (JoystickView) findViewById(R.id.joystick2);
        leftStick.setAutoReCenterButton(true);
        rightStick.setAutoReCenterButton(true);

        TextView textView1 = (TextView) findViewById(R.id.textView1);

        leftStick.setOnMoveListener(new JoystickView.OnMoveListener() {
            @Override
            public void onMove(int angle, int strength) {
                if (angle == 90) {
                    leftjoystickStrength    = strength;
                } else {
                    leftjoystickStrength = -strength;
                }
            }
        },100);

        rightStick.setOnMoveListener(new JoystickView.OnMoveListener() {
            @Override
            public void onMove(int angle, int strength) {
                if (angle == 90) {
                    rightjoystickStrength = strength;
                } else {
                    rightjoystickStrength = -strength;
                }
            }
        },100);



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

        startJoystickSender();
    }
    private void startJoystickSender() {
        executorService.execute(() -> {
            while (isSending) {
                String command;
                String message;

                int left = leftjoystickStrength;
                int right = rightjoystickStrength;

                if (left == 0 && right == 0) {
                    if (isStopped) {
                        continue;  // Skip sending if already stopped
                    }
                    command = "stop";
                    isStopped = true;
                } else {
                    command = "drv";
                    isStopped = false;
                }

                message = String.format(Locale.CANADA, "%d,%d", left, right);

                DataPacket dataPacket = new DataPacket(command, message);
                boolean isSent = TcpClient.getInstance().sendPacket(dataPacket.toBytes());

                if (!isSent) {
                    mainHandler.post(() -> showToast("Failed to send data"));
                }

                try {
                    Thread.sleep(500);  // 500ms delay
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            }
        });
    }

    /**
     * Sends the joystick angle and strength to the TCP server (Pico W).
     */
    private void sendTcpPacket(String command, String message) {

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