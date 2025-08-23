#ifndef ENCODER_H
#define ENCODER_H

#include <Arduino.h>
#include "config.h"

// ====== ENCODER STATE ======
extern volatile int64_t positionCounts;
extern volatile int8_t  lastStateAB;
extern volatile uint32_t lastEdgeMicros;
extern volatile uint32_t edgeDeltaMicros;
extern volatile bool indexFlag;

extern float emaCountsPerSec;
extern int64_t lastSamplePos;

// ====== ENCODER FUNCTIONS ======
void initEncoder();
void updateEncoderSpeed(uint32_t currentTime);
float getRPM();
float getRevolutionsPerSecond();
int64_t getPosition();

// ====== INTERRUPT SERVICE ROUTINES ======
IRAM_ATTR void isrA();
IRAM_ATTR void isrB();
IRAM_ATTR void isrZ();
IRAM_ATTR void updateFromAB();

// ====== UTILITY FUNCTIONS ======
inline uint32_t micros_fast();

#endif // ENCODER_H
