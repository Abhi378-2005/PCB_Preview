/*
 * gcode.h — G-Code interpreter for PCB Plotter
 *
 * Parses and executes standard G-code commands.
 *
 * Supported commands:
 *   G0  Xn Yn          — Rapid move (max speed)
 *   G1  Xn Yn Fn       — Linear move at feed rate F (mm/min)
 *   G4  Pn             — Dwell for P milliseconds
 *   G21                — Set units to millimeters
 *   G28                — Home all axes
 *   G90                — Absolute positioning mode
 *   G91                — Relative positioning mode
 *   M2                 — Program end
 *
 * Comments:
 *   Lines starting with ';' are ignored
 *   Inline comments after ';' are stripped
 *
 * Usage:
 *   initGCode();
 *   executeGCodeLine("G0 X10 Y20");
 *   executeGCodeLine("G1 X50 Y30 F1000");
 */

#ifndef GCODE_H
#define GCODE_H

#include <Arduino.h>

/**
 * Initialize the G-code interpreter state.
 * Resets position, feed rate, and mode to defaults.
 */
void initGCode();

/**
 * Parse and execute a single line of G-code.
 *
 * @param line  null-terminated G-code string (e.g. "G1 X10 Y20 F1000")
 * @return true if command was executed successfully, false on error
 */
bool executeGCodeLine(const char* line);

/**
 * Execute a complete G-code program from a string buffer.
 * Splits on newlines and executes each line.
 *
 * @param program  null-terminated multi-line G-code string
 * @return number of lines executed
 */
int executeGCodeProgram(const char* program);

/**
 * Check if the interpreter has received M2 (program end).
 */
bool isGCodeFinished();

/**
 * Reset the interpreter (clear finished flag, reset state).
 */
void resetGCode();

#endif // GCODE_H
