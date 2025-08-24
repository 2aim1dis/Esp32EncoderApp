// ESP32-S3 Quadrature Encoder Reader (Omron E6B2-CWZ6C)
// Pins: A=GPIO16 (black), B=GPIO17 (white), Z=GPIO18 (orange, optional)
// Pull-ups: External 4.7k to 3.3V (encoder outputs are open-collector; powered from 5V but logic pulled to 3V3)
// Board (Arduino IDE): ESP32S3 Dev Module (adjust flash/PSRAM as needed)

#include <Arduino.h>
#include "config.h"
#include "encoder.h"
#include "loadcell.h"
#include "commands.h"
#include "display.h"

void setup() {
  Serial.begin(115200);
  delay(300);
  
  // Print system information
  printSystemStatus();
  
  // Initialize subsystems
  initEncoder();
  initLoadCell();
}

void loop() {
  uint32_t currentTime = micros_fast();
  
  // Update load cell readings for both loadcells
  updateLoadCell(0, currentTime); // LoadCell 1
  updateLoadCell(1, currentTime); // LoadCell 2
  
  // Update encoder speed calculations
  updateEncoderSpeed(currentTime);
  
  // Handle serial commands
  processSerialCommands();
  
  // Check if it's time to output data
  static uint32_t lastOutput = 0;
  if ((uint32_t)(currentTime - lastOutput) >= SPEED_SAMPLE_US) {
    // Get current readings
    int64_t position = getPosition();
    float rpm = getRPM();
    float countsPerSec = emaCountsPerSec;
    float forceKg1 = getForceKg(0); // LoadCell 1
    float forceKg2 = getForceKg(1); // LoadCell 2
    
    // Check for index pulse
    bool indexSeen;
    noInterrupts();
    indexSeen = indexFlag;
    indexFlag = false;
    interrupts();
    
    // Print combined output
    printEncoderData(position, rpm, countsPerSec, indexSeen);
    printForceData(forceKg1); // LoadCell 1
    printForceData(forceKg2); // LoadCell 2
    
    lastOutput = currentTime;
  }
}
