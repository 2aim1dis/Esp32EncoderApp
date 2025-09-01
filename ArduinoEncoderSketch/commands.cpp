#include "commands.h"
#include "loadcell.h"
#include "encoder.h"

void processSerialCommands() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    if (cmd.equalsIgnoreCase("TARE")) {
      handleTareCommand();
    } else if (cmd.startsWith("CAL")) {
      handleCalCommand(cmd);
    } else if (cmd.equalsIgnoreCase("RAW")) {
      handleRawCommand();
    } else if (cmd.equalsIgnoreCase("SCALE")) {
      handleScaleCommand();
    } else if (cmd.equalsIgnoreCase("ZERO")) {
      handleZeroCommand();
    } else if (cmd.length() > 0) {
      Serial.println(F("Unknown command. Available: TARE, CAL <kg>, RAW, SCALE, ZERO"));
    }
  }
}

void handleTareCommand() {
  tareLoadCell();
}

void handleCalCommand(const String& cmd) {
  // Format: CAL 10.0  (known weight in kg currently applied)
  int spaceIdx = cmd.indexOf(' ');
  if (spaceIdx > 0) {
    float known = cmd.substring(spaceIdx + 1).toFloat();
    if (known > 0.0f) {
      calibrateLoadCell(known);
    } else {
      Serial.println(F("CAL ERR - Weight must be positive"));
    }
  } else {
    Serial.println(F("CAL usage: CAL <kg>"));
  }
}

void handleRawCommand() {
  Serial.print(F("RAW="));
  Serial.println(getRawReading());
}

void handleScaleCommand() {
  Serial.print(F("SCALE="));
  Serial.println(getScaleFactor(), 6);
}

void handleZeroCommand() {
  resetPosition();
  Serial.println(F("Encoder position reset to zero"));
}
