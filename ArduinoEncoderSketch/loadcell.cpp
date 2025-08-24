#include "loadcell.h"

// ====== LOAD CELL STATE ======
// Initial scale: counts per kg (placeholder). Will be replaced by CAL command.
// After calibration: scale = (raw - offset) / known_weight_kg
float hx711ScaleCountsPerKg[NUM_LOADCELLS] = {1000.0f, 1000.0f}; // UPDATE after CAL
int32_t hx711Offset[NUM_LOADCELLS] = {0, 0};               // Tare offset
bool hx711Tared[NUM_LOADCELLS] = {false, false};
float filteredForceKg[NUM_LOADCELLS] = {0.0f, 0.0f};
int32_t lastHxRaw[NUM_LOADCELLS] = {0, 0};                 // last averaged raw
uint32_t lastForceUpdateUs[NUM_LOADCELLS] = {0, 0};

// Static variables for sampling state (per loadcell)
static int32_t hxAccum[NUM_LOADCELLS] = {0, 0};
static uint8_t hxCount[NUM_LOADCELLS] = {0, 0};

// Pin arrays for each loadcell
static const uint8_t doutPins[NUM_LOADCELLS] = {HX711_DOUT_PIN_1, HX711_DOUT_PIN_2};
static const uint8_t sckPins[NUM_LOADCELLS] = {HX711_SCK_PIN_1, HX711_SCK_PIN_2};

void initLoadCell() {
  Serial.println(F("Initializing Load Cells (HX711)..."));
  
  for (uint8_t i = 0; i < NUM_LOADCELLS; i++) {
    // Configure HX711 pins for each loadcell
    pinMode(sckPins[i], OUTPUT);
    pinMode(doutPins[i], INPUT); // DOUT floats high until data ready (goes LOW)
    
    // Reset the HX711
    digitalWrite(sckPins[i], LOW);
    Serial.printf("LoadCell %d initialized on pins DOUT=%d, SCK=%d\n", i+1, doutPins[i], sckPins[i]);
  }
  delay(100);
}

void updateLoadCell(uint8_t cellIndex, uint32_t currentTime) {
  if (cellIndex >= NUM_LOADCELLS) return; // Safety check
  
  // ---- Non-blocking HX711 sampling (collect up to HX711_READ_SAMPLES each loop batch) ----
  // HX711 data ready when DOUT LOW.
  if (digitalRead(doutPins[cellIndex]) == LOW) {
    // Read one sample (24-bit two's complement, channel A, gain 128)
    uint32_t value = 0;
    
    // Disable interrupts very briefly to minimize jitter on clock (keep short!)
    noInterrupts();
    for (uint8_t i = 0; i < 24; ++i) {
      digitalWrite(sckPins[cellIndex], HIGH);
      // small delay; on S3 fast toggling acceptable; optionally delayMicroseconds(1);
      value = (value << 1) | (uint32_t)digitalRead(doutPins[cellIndex]);
      digitalWrite(sckPins[cellIndex], LOW);
    }
    // Set gain (1 extra pulse for 128 gain channel A)
    digitalWrite(sckPins[cellIndex], HIGH);
    digitalWrite(sckPins[cellIndex], LOW);
    interrupts();
    
    // Sign extend 24-bit two's complement
    if (value & 0x800000UL) value |= 0xFF000000UL;
    int32_t signedVal = (int32_t)value;
    hxAccum[cellIndex] += signedVal;
    hxCount[cellIndex]++;
  }

  // Periodically update filtered force (after collecting samples or if timeout)
  if ((hxCount[cellIndex] >= HX711_READ_SAMPLES) || ((uint32_t)(currentTime - lastForceUpdateUs[cellIndex]) > 100000)) { // 100ms in microseconds
    if (hxCount[cellIndex] > 0) {
      int32_t avgRaw = hxAccum[cellIndex] / hxCount[cellIndex];
      lastHxRaw[cellIndex] = avgRaw;
      
      if (!hx711Tared[cellIndex]) { // First time establish tare baseline
        hx711Offset[cellIndex] = avgRaw;
        hx711Tared[cellIndex] = true;
      }
      
      int32_t diff = avgRaw - hx711Offset[cellIndex];
      float instKg = (hx711ScaleCountsPerKg[cellIndex] > 0.0f) ? (diff / hx711ScaleCountsPerKg[cellIndex]) : 0.0f;
      
      // IIR filter
      filteredForceKg[cellIndex] = FORCE_IIR_ALPHA * instKg + (1.0f - FORCE_IIR_ALPHA) * filteredForceKg[cellIndex];
      lastForceUpdateUs[cellIndex] = currentTime;
    }
    hxAccum[cellIndex] = 0;
    hxCount[cellIndex] = 0;
  }
}

void tareLoadCell(uint8_t cellIndex) {
  if (cellIndex >= NUM_LOADCELLS) return; // Safety check
  hx711Offset[cellIndex] = lastHxRaw[cellIndex];
  hx711Tared[cellIndex] = true;
  Serial.printf("TARE OK for LoadCell %d\n", cellIndex + 1);
}

void calibrateLoadCell(uint8_t cellIndex, float knownWeightKg) {
  if (cellIndex >= NUM_LOADCELLS) return; // Safety check
  if (knownWeightKg > 0.0f) {
    int32_t diff = lastHxRaw[cellIndex] - hx711Offset[cellIndex];
    hx711ScaleCountsPerKg[cellIndex] = diff / knownWeightKg; // counts per kg
    Serial.printf("CAL OK for LoadCell %d scale counts/kg=%.3f\n", cellIndex + 1, hx711ScaleCountsPerKg[cellIndex]);
  } else {
    Serial.printf("CAL ERR for LoadCell %d - Weight must be positive\n", cellIndex + 1);
  }
}

float getForceKg(uint8_t cellIndex) {
  if (cellIndex >= NUM_LOADCELLS) return 0.0f; // Safety check
  return filteredForceKg[cellIndex];
}

int32_t getRawReading(uint8_t cellIndex) {
  if (cellIndex >= NUM_LOADCELLS) return 0; // Safety check
  return lastHxRaw[cellIndex];
}

float getScaleFactor(uint8_t cellIndex) {
  if (cellIndex >= NUM_LOADCELLS) return 0.0f; // Safety check
  return hx711ScaleCountsPerKg[cellIndex];
}
}
