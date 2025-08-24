#ifndef LOADCELL_H
#define LOADCELL_H

#include <Arduino.h>
#include "config.h"

// ====== LOAD CELL STATE ======
extern float hx711ScaleCountsPerKg;
extern int32_t hx711Offset;
extern bool hx711Tared;
extern float filteredForceKg;
extern int32_t lastHxRaw;
extern uint32_t lastForceUpdateUs;

// ====== LOAD CELL FUNCTIONS ======
void initLoadCell();
void updateLoadCell(uint32_t currentTime);
void tareLoadCell();
void calibrateLoadCell(float knownWeightKg);
float getForceKg();
int32_t getRawReading();
float getScaleFactor();

#endif // LOADCELL_H
