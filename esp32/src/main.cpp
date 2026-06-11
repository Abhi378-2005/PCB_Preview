/*
 * main.cpp — PCB Plotter Entry Point (Phase 5)
 *
 * ESP32-WROOM-32 + 2x TMC2209 (standalone, 1/16 microstepping)
 *
 * Features:
 *   - Web UI D-pad jog control (via wifi_server)
 *   - G-code interpreter (via gcode module)
 *   - Serial G-code input: paste G-code into serial monitor
 *
 * Modules:
 *   motion       — GPIO setup, stepper pulses, Bresenham XY movement
 *   gcode        — G-code parser and executor
 *   wifi_server  — WiFi connection, HTTP server, HTML UI
 */

#include <Arduino.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "motion.h"
#include "gcode.h"
#include "wifi_server.h"

// ── Serial input buffer ───────────────────────────────────────────
static char serialBuffer[256];
static int serialIdx = 0;

void setup() {
    // Disable brownout detector to prevent reset on current spikes (e.g. WiFi startup)
    WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);

    Serial.begin(115200);
    delay(2000);

    Serial.println("=========================================");
    Serial.println("  PCB Plotter — Phase 5");
    Serial.println("  ESP32 + TMC2209 + G-Code Interpreter");
    Serial.println("=========================================");

    initMotion();      // configure STEP/DIR GPIO pins
    initGCode();       // initialize G-code interpreter
    initWiFi();        // scan networks + connect to AP
    initWebServer();   // register routes + start HTTP server

    Serial.println();
    Serial.println("[main] Ready! You can:");
    Serial.println("  1. Use the Web UI D-pad at http://<IP>/");
    Serial.println("  2. Paste G-code lines into this serial monitor");
    Serial.println();
    Serial.println("Example G-code commands:");
    Serial.println("  G0 X10 Y10       (rapid move)");
    Serial.println("  G1 X50 Y30 F1000 (draw at 1000mm/min)");
    Serial.println("  G28              (home)");
    Serial.println("  G4 P500          (dwell 500ms)");
    Serial.println("=========================================");
}

void loop() {
    // Handle web server requests
    handleServer();

    // Handle serial G-code input
    while (Serial.available()) {
        char c = Serial.read();

        if (c == '\n' || c == '\r') {
            if (serialIdx > 0) {
                serialBuffer[serialIdx] = '\0';

                // Check for special commands
                if (strcmp(serialBuffer, "status") == 0 || strcmp(serialBuffer, "?") == 0) {
                    Serial.printf("[status] Position: (%.2f, %.2f) mm\n",
                                  getPositionX(), getPositionY());
                    Serial.printf("[status] G-code finished: %s\n",
                                  isGCodeFinished() ? "yes" : "no");
                } else if (strcmp(serialBuffer, "reset") == 0) {
                    resetGCode();
                    Serial.println("[main] G-code interpreter reset");
                } else if (strcmp(serialBuffer, "stop") == 0) {
                    setStopFlag(true);
                    Serial.println("[main] STOP flag set");
                } else {
                    // Execute as G-code
                    setStopFlag(false);  // clear stop flag before new command
                    executeGCodeLine(serialBuffer);
                }

                serialIdx = 0;
            }
        } else {
            if (serialIdx < (int)sizeof(serialBuffer) - 1) {
                serialBuffer[serialIdx++] = c;
            }
        }
    }
}
