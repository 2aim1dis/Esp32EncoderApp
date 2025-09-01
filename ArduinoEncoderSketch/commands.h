#ifndef COMMANDS_H
#define COMMANDS_H

#include <Arduino.h>

// ====== COMMAND PROCESSING ======
void processSerialCommands();
void handleTareCommand();
void handleCalCommand(const String& cmd);
void handleRawCommand();
void handleScaleCommand();
void handleZeroCommand();

#endif // COMMANDS_H
