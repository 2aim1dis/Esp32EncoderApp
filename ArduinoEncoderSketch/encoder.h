#ifndef ENCODER_H
#define ENCODER_H

#include <Arduino.h>
#include "config.h"

#if USE_HARDWARE_PCNT
#include "driver/pcnt.h"
#include "soc/gpio_struct.h"
#endif

// ====== ENCODER STATE ======
extern volatile int64_t positionCounts;
extern volatile int8_t  lastStateAB;
extern volatile uint32_t lastEdgeMicros;
extern volatile uint32_t edgeDeltaMicros;
extern volatile bool indexFlag;
extern volatile int8_t lastDeltaSign;  // Sign of last delta for signed edge speed

extern float emaCountsPerSec;
extern int64_t lastSamplePos;

#if USE_HARDWARE_PCNT
extern pcnt_unit_t pcnt_unit;
extern int16_t pcnt_overflow_count;
#endif

// ====== ENCODER FUNCTIONS ======
void initEncoder();
void updateEncoderSpeed(uint32_t currentTime);
float getRPM();
float getRevolutionsPerSecond();
int64_t getPosition();
void resetPosition();  // Reset position to zero
void setPosition(int64_t newPos);  // Set position to specific value

#if USE_HARDWARE_PCNT
// PCNT specific functions
void initPCNT();
int64_t readPCNTPosition();
IRAM_ATTR void pcnt_overflow_handler(void* arg);
#else
// ISR specific functions (optimized)
IRAM_ATTR void isrA();
IRAM_ATTR void isrB();
IRAM_ATTR void updateFromAB_Fast();
#endif

IRAM_ATTR void isrZ();

// ====== UTILITY FUNCTIONS ======
inline uint32_t micros_fast();

#endif // ENCODER_H
