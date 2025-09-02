#ifndef DISPLAY_H
#define DISPLAY_H

#include <Arduino.h>

// ====== DISPLAY FUNCTIONS ======
void printSystemStatus();
void printEncoderData(int64_t position, float rpm, float countsPerSec, bool indexSeen);

#endif // DISPLAY_H
