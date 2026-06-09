/*
 * motion.cpp — Stepper motor pulse generation & coordinate movement
 *
 * Extracted from monolithic main.cpp, extended for Phase 5.
 * Drives TMC2209 drivers in standalone mode via STEP/DIR signals.
 *
 * Features:
 *   - Single-axis step pulse generation
 *   - Bresenham synchronized XY movement
 *   - Position tracking in mm
 *   - Feed rate control (mm/min)
 *   - Emergency stop flag
 */

#include "motion.h"

// ── State ─────────────────────────────────────────────────────────
static volatile bool stopFlag = false;
static float currentX = 0.0;  // current position in mm
static float currentY = 0.0;

// ── Public API ────────────────────────────────────────────────────

void initMotion() {
    pinMode(X_STEP_PIN, OUTPUT);
    pinMode(X_DIR_PIN,  OUTPUT);
    pinMode(Y_STEP_PIN, OUTPUT);
    pinMode(Y_DIR_PIN,  OUTPUT);

    currentX = 0.0;
    currentY = 0.0;

    Serial.println("[motion] GPIO initialized");
    Serial.printf("[motion] X: STEP=%d DIR=%d\n", X_STEP_PIN, X_DIR_PIN);
    Serial.printf("[motion] Y: STEP=%d DIR=%d\n", Y_STEP_PIN, Y_DIR_PIN);
    Serial.printf("[motion] Timing: pulse=%dus delay=%dus\n", PULSE_WIDTH_US, STEP_DELAY_US);
    Serial.printf("[motion] Resolution: %d steps/mm\n", STEPS_PER_MM);
}

void stepMotor(uint8_t stepPin, uint8_t dirPin, int dir, int steps) {
    digitalWrite(dirPin, dir ? HIGH : LOW);
    delayMicroseconds(5); // settle direction signal

    for (int i = 0; i < steps && !stopFlag; i++) {
        digitalWrite(stepPin, HIGH);
        delayMicroseconds(PULSE_WIDTH_US);
        digitalWrite(stepPin, LOW);
        delayMicroseconds(STEP_DELAY_US);
    }
}

void moveToXY(float x_mm, float y_mm, float feed_rate) {
    // Calculate delta in steps
    long targetX = (long)(x_mm * STEPS_PER_MM);
    long targetY = (long)(y_mm * STEPS_PER_MM);
    long curX = (long)(currentX * STEPS_PER_MM);
    long curY = (long)(currentY * STEPS_PER_MM);

    long dx = targetX - curX;
    long dy = targetY - curY;

    // Nothing to do
    if (dx == 0 && dy == 0) return;

    // Direction
    int xDir = (dx >= 0) ? 1 : 0;
    int yDir = (dy >= 0) ? 1 : 0;

    long absDx = abs(dx);
    long absDy = abs(dy);

    // Set direction pins
    digitalWrite(X_DIR_PIN, xDir ? HIGH : LOW);
    digitalWrite(Y_DIR_PIN, yDir ? HIGH : LOW);
    delayMicroseconds(5); // settle direction

    // Calculate step delay from feed rate
    // feed_rate is in mm/min, convert to us per step
    unsigned long stepDelay;
    if (feed_rate <= 0) {
        // Rapid move — use minimum delay
        stepDelay = STEP_DELAY_US;
    } else {
        // Calculate actual distance for speed computation
        float dist_mm = sqrt((float)(dx * dx + dy * dy)) / STEPS_PER_MM;
        float total_steps = max(absDx, absDy);

        if (total_steps == 0) return;

        // Time for entire move in seconds
        float time_sec = (dist_mm / feed_rate) * 60.0;
        // Time per step in microseconds
        stepDelay = (unsigned long)((time_sec * 1000000.0) / total_steps);

        // Clamp to reasonable range
        if (stepDelay < PULSE_WIDTH_US + 5) stepDelay = PULSE_WIDTH_US + 5;
        if (stepDelay > 50000) stepDelay = 50000;  // max 50ms per step = very slow
    }

    // Bresenham line algorithm for synchronized XY movement
    long steps = max(absDx, absDy);
    long errX = 0;
    long errY = 0;

    Serial.printf("[motion] moveToXY(%.2f, %.2f) steps=%ld delay=%luus\n",
                  x_mm, y_mm, steps, stepDelay);

    for (long i = 0; i < steps && !stopFlag; i++) {
        errX += absDx;
        errY += absDy;

        bool stepX = false;
        bool stepY = false;

        if (errX >= steps) {
            errX -= steps;
            stepX = true;
        }
        if (errY >= steps) {
            errY -= steps;
            stepY = true;
        }

        // Pulse step pins simultaneously for synchronized movement
        if (stepX) digitalWrite(X_STEP_PIN, HIGH);
        if (stepY) digitalWrite(Y_STEP_PIN, HIGH);

        delayMicroseconds(PULSE_WIDTH_US);

        if (stepX) digitalWrite(X_STEP_PIN, LOW);
        if (stepY) digitalWrite(Y_STEP_PIN, LOW);

        delayMicroseconds(stepDelay);
    }

    // Update position (even if stopped early, track actual position)
    if (!stopFlag) {
        currentX = x_mm;
        currentY = y_mm;
    }
}

void moveRelative(float dx_mm, float dy_mm, float feed_rate) {
    moveToXY(currentX + dx_mm, currentY + dy_mm, feed_rate);
}

void home() {
    Serial.println("[motion] Homing to (0, 0)");
    moveToXY(0.0, 0.0, 0);  // rapid move to origin
}

float getPositionX() {
    return currentX;
}

float getPositionY() {
    return currentY;
}

void setStopFlag(bool flag) {
    stopFlag = flag;
}

bool getStopFlag() {
    return stopFlag;
}
