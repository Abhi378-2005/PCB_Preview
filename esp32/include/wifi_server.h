/*
 * wifi_server.h — WiFi connection and Web UI server for PCB Plotter
 *
 * Serves a D-pad control interface over HTTP.
 * Endpoints:
 *   GET  /       → HTML UI with jog controls
 *   POST /move   → body: axis=x&dir=1&steps=160
 *   GET  /stop   → emergency stop
 */

#ifndef WIFI_SERVER_H
#define WIFI_SERVER_H

#include <Arduino.h>

/**
 * Scan for networks, then connect to the configured WiFi AP.
 * Blocks until connected. Prints IP address to Serial.
 */
void initWiFi();

/**
 * Register HTTP routes and start the web server on port 80.
 * Must be called after initWiFi().
 */
void initWebServer();

/**
 * Process pending HTTP requests.
 * Must be called in loop().
 */
void handleServer();

#endif // WIFI_SERVER_H
