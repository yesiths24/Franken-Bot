package com.example.frankenbotapp;

import androidx.appcompat.app.AppCompatActivity;

import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.view.View;
import android.widget.ArrayAdapter;
import android.widget.AutoCompleteTextView;
import android.widget.ImageView;
import android.widget.TextView;
import android.widget.Toast;

import java.io.IOException;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

import io.github.controlwear.virtual.joystick.android.JoystickView;

public class ManualActivity extends AppCompatActivity {
    private final ExecutorService executorService = Executors.newSingleThreadExecutor();
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private volatile int leftjoystickStrength = 0;
    private volatile int rightjoystickStrength = 0;
    private volatile boolean modeChanged = false;
    private volatile boolean isSending = true;
    private volatile boolean isStopped = false;
    private final ExecutorService streamExecutor = Executors.newSingleThreadExecutor();
    private final Handler uiHandler = new Handler(Looper.getMainLooper());
    private TcpClient tcpClient = TcpClient.getInstance();
    private int mode = 0; // 0 for manual, 1 for automatic, 2 for tracking
    private static final long MODE_DEBOUNCE_MS = 600;   // ignore re‑clicks < 600 ms apart
    private long lastModeClickTime = 0;

    String[] modes = {"manual", "tag", "track"};

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
                textView1.setText(String.format(Locale.CANADA, "%d,%d", leftjoystickStrength, rightjoystickStrength));
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
                textView1.setText(String.format(Locale.CANADA, "%d,%d", leftjoystickStrength, rightjoystickStrength));
            }
        },100);


        AutoCompleteTextView autoCompleteTextView = findViewById(R.id.autoCompleteTextView1);
        //set default mode to manual
        autoCompleteTextView.setText(modes[0], false);
        modeChanged = true; //to make sure bot starts in manual mode
        autoCompleteTextView.setAdapter(
                new ArrayAdapter<>(this, android.R.layout.simple_dropdown_item_1line, modes));

        autoCompleteTextView.setOnItemClickListener((parent, view, position, id) -> {
            String targetMode = (String) parent.getItemAtPosition(position);

            // Disable the picker while we fire the packet (prevents double‑clicks)
            autoCompleteTextView.setEnabled(false);

            modeChanged = true;
            mode = position;
        });




        startCommandSender();
        startImageStream();
    }

    private void adjustUIForMode(int mode) {
        // Adjust UI elements based on the selected mode
        JoystickView leftStick = findViewById(R.id.joystick1);
        JoystickView rightStick = findViewById(R.id.joystick2);
        switch (mode) {
            case 0: // Manual mode
                // Enable joystick controls
                leftStick.setEnabled(true);
                rightStick.setEnabled(true);
                leftStick.setVisibility(View.VISIBLE);
                rightStick.setVisibility(View.VISIBLE);
                break;
            case 1: // Automatic mode
                // Disable joystick controls
                leftStick.setEnabled(false);
                rightStick.setEnabled(false);
                leftStick.setVisibility(View.INVISIBLE);
                rightStick.setVisibility(View.INVISIBLE);

                break;
            case 2: // Tracking mode
                // Disable joystick controls
                leftStick.setEnabled(false);
                rightStick.setEnabled(false);
                leftStick.setVisibility(View.INVISIBLE);
                rightStick.setVisibility(View.INVISIBLE);
                break;
            default:
                break;
        }
    }
    private void startCommandSender() {
        executorService.execute(() -> {
            while (isSending) {
                String command;
                String message;

                int left = leftjoystickStrength;
                int right = rightjoystickStrength;
                if (modeChanged) {
                    command = "mode";
                    message = modes[mode];
                    modeChanged = false;
                    tcpClient.sendPacket(new DataPacket(command, message).toBytes());
                    mainHandler.post(() -> showToast("Mode changed to: " + modes[mode]));
                    mainHandler.post(() -> {
                        AutoCompleteTextView autoCompleteTextView = findViewById(R.id.autoCompleteTextView1);
                        autoCompleteTextView.setEnabled(true);  // Re-enable the picker
                        adjustUIForMode(mode);  // Adjust UI based on the new mode
                    });
                    continue;  // Skip sending joystick data if mode changed
                }
                if (mode != 0) {
                    continue;  // Skip sending joystick data if not in manual mode
                }

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
                boolean isSent = tcpClient.sendPacket(dataPacket.toBytes());

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

    private void startImageStream() {
        //Send a ack to get start streaming
        streamExecutor.execute(() -> {


            ImageView imageView1 = findViewById(R.id.imageView1);
            TextView statusText  = findViewById(R.id.textView1);   // optional

            while (!Thread.currentThread().isInterrupted()) {
                try {
                    /* ---------- one frame ---------- */
                    byte[] imageData = tcpClient.receiveImageBytes();

                    if (imageData == null || imageData.length == 0) {
                        continue;                                       // skip empty frame
                    }

                    Bitmap bmp = BitmapFactory.decodeByteArray(imageData, 0, imageData.length);
                    if (bmp != null) {
                        uiHandler.post(() -> imageView1.setImageBitmap(bmp));
                    }
                }
                /* ---------- per‑frame error handling ---------- */
                catch (IOException ioe) {                               // network / read error
                    ioe.printStackTrace();
                    uiHandler.post(() -> statusText.setText("Frame dropped: " + ioe.getMessage()));
                    // Give the socket a tiny breather before retrying
                    try { Thread.sleep(50); } catch (InterruptedException ex) {
                        Thread.currentThread().interrupt();
                    }
                }
                catch (Exception ex) {                                  // decoding, OOM, etc.
                    ex.printStackTrace();
                    uiHandler.post(() -> statusText.setText("Stream error: " + ex.getMessage()));
                }
            }
        });
    }


    private void showToast(String message) {
        runOnUiThread(() -> Toast.makeText(ManualActivity.this, message, Toast.LENGTH_LONG).show());
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();

        // Stop the command sender
        isSending = false;

        // Stop image stream thread
        streamExecutor.shutdownNow();
        executorService.shutdownNow();

        // Close TCP connection
        Executors.newSingleThreadExecutor().execute(
                () -> TcpClient.getInstance().disconnect());
    }
}