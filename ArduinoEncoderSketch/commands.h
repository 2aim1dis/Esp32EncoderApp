#ifndef COMMANDS_H
#define COMMANDS_H

#include <Arduino.h>

// ====== COMMAND PROCESSING ======
void processSerialCommands();
void handleTareCommand();
void handleTareCommand(const String& cmd);
void handleCalCommand(const String& cmd);
void handleRawCommand();
void handleScaleCommand();

#endif // COMMANDS_H
