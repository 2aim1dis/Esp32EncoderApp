#include "commands.h"
#include "loadcell.h"

void processSerialCommands() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    if (cmd.equalsIgnoreCase("TARE")) {
      handleTareCommand();
    } else if (cmd.startsWith("TARE")) {
      handleTareCommand(cmd);
    } else if (cmd.startsWith("CAL")) {
      handleCalCommand(cmd);
    } else if (cmd.equalsIgnoreCase("RAW")) {
      handleRawCommand();
    } else if (cmd.equalsIgnoreCase("SCALE")) {
      handleScaleCommand();
    } else if (cmd.length() > 0) {
      Serial.println(F("Unknown command. Available: TARE [1|2], CAL <cellIndex> <kg>, RAW, SCALE"));
    }
  }
}

void handleTareCommand() {
  // Tare both loadcells
  for (uint8_t i = 0; i < NUM_LOADCELLS; i++) {
    tareLoadCell(i);
  }
}

void handleTareCommand(const String& cmd) {
  // Format: TARE 1 or TARE 2 (specific loadcell)
  int spaceIdx = cmd.indexOf(' ');
  if (spaceIdx > 0) {
    uint8_t cellIndex = cmd.substring(spaceIdx + 1).toInt() - 1; // Convert to 0-based index
    if (cellIndex < NUM_LOADCELLS) {
      tareLoadCell(cellIndex);
    } else {
      Serial.printf("TARE ERR - LoadCell index must be 1-%d\n", NUM_LOADCELLS);
    }
  } else {
    handleTareCommand(); // Tare all
  }
}

void handleCalCommand(const String& cmd) {
  // Format: CAL 1 10.0  (loadcell index and known weight in kg currently applied)
  int spaceIdx1 = cmd.indexOf(' ');
  if (spaceIdx1 > 0) {
    int spaceIdx2 = cmd.indexOf(' ', spaceIdx1 + 1);
    if (spaceIdx2 > 0) {
      uint8_t cellIndex = cmd.substring(spaceIdx1 + 1, spaceIdx2).toInt() - 1; // Convert to 0-based
      float known = cmd.substring(spaceIdx2 + 1).toFloat();
      if (cellIndex < NUM_LOADCELLS && known > 0.0f) {
        calibrateLoadCell(cellIndex, known);
      } else {
        Serial.printf("CAL ERR - LoadCell index must be 1-%d and weight positive\n", NUM_LOADCELLS);
      }
    } else {
      Serial.println(F("CAL usage: CAL <cellIndex> <kg>"));
    }
  } else {
    Serial.println(F("CAL usage: CAL <cellIndex> <kg>"));
  }
}

void handleRawCommand() {
  for (uint8_t i = 0; i < NUM_LOADCELLS; i++) {
    Serial.printf("RAW%d=%ld ", i+1, getRawReading(i));
  }
  Serial.println();
}

void handleScaleCommand() {
  for (uint8_t i = 0; i < NUM_LOADCELLS; i++) {
    Serial.printf("SCALE%d=%.6f ", i+1, getScaleFactor(i));
  }
  Serial.println();
}
