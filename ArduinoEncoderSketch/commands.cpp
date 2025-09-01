#include "commands.h"
#include "encoder.h"

void processSerialCommands() {
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    if (cmd.equalsIgnoreCase("ZERO")) {
      handleZeroCommand();
    } else if (cmd.length() > 0) {
      Serial.println(F("Unknown command. Available: ZERO"));
    }
  }
}

void handleZeroCommand() {
  resetPosition();
  Serial.println(F("Encoder position reset to zero"));
}
