#ifndef LOADCELL_H
#define LOADCELL_H

#include <Arduino.h>
#include "config.h"

// ====== LOAD CELL STATE ======
// LoadCell arrays for multiple load cells
extern float hx711ScaleCountsPerKg[NUM_LOADCELLS];
extern int32_t hx711Offset[NUM_LOADCELLS];
extern bool hx711Tared[NUM_LOADCELLS];
extern float filteredForceKg[NUM_LOADCELLS];
extern int32_t lastHxRaw[NUM_LOADCELLS];
extern uint32_t lastForceUpdateUs[NUM_LOADCELLS];

// ====== LOAD CELL FUNCTIONS ======
void initLoadCell();
void updateLoadCell(uint8_t cellIndex, uint32_t currentTime);
void tareLoadCell(uint8_t cellIndex);
void calibrateLoadCell(uint8_t cellIndex, float knownWeightKg);
float getForceKg(uint8_t cellIndex);
int32_t getRawReading(uint8_t cellIndex);
float getScaleFactor(uint8_t cellIndex);

#endif // LOADCELL_H
