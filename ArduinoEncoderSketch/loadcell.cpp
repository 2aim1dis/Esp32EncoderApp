#include "loadcell.h"

// ====== LOAD CELL STATE ======
// Initial scale: counts per kg (placeholder). Will be replaced by CAL command.
// After calibration: scale = (raw - offset) / known_weight_kg
float hx711ScaleCountsPerKg = 1000.0f; // UPDATE after CAL
int32_t hx711Offset = 0;               // Tare offset
bool hx711Tared = false;
float filteredForceKg = 0.0f;
int32_t lastHxRaw = 0;                 // last averaged raw
uint32_t lastForceUpdateMs = 0;

// Static variables for sampling state
static int32_t hxAccum = 0;
static uint8_t hxCount = 0;

void initLoadCell() {
  Serial.println(F("Initializing Load Cell (HX711)..."));
  
  // Configure HX711 pins
  pinMode(HX711_SCK_PIN, OUTPUT);
  pinMode(HX711_DOUT_PIN, INPUT); // DOUT floats high until data ready (goes LOW)
  
  // Reset the HX711
  digitalWrite(HX711_SCK_PIN, LOW);
  delay(100);
}

void updateLoadCell() {
  // ---- Non-blocking HX711 sampling (collect up to HX711_READ_SAMPLES each loop batch) ----
  // HX711 data ready when DOUT LOW.
  if (digitalRead(HX711_DOUT_PIN) == LOW) {
    // Read one sample (24-bit two's complement, channel A, gain 128)
    uint32_t value = 0;
    
    // Disable interrupts very briefly to minimize jitter on clock (keep short!)
    noInterrupts();
    for (uint8_t i = 0; i < 24; ++i) {
      digitalWrite(HX711_SCK_PIN, HIGH);
      // small delay; on S3 fast toggling acceptable; optionally delayMicroseconds(1);
      value = (value << 1) | (uint32_t)digitalRead(HX711_DOUT_PIN);
      digitalWrite(HX711_SCK_PIN, LOW);
    }
    // Set gain (1 extra pulse for 128 gain channel A)
    digitalWrite(HX711_SCK_PIN, HIGH);
    digitalWrite(HX711_SCK_PIN, LOW);
    interrupts();
    
    // Sign extend 24-bit two's complement
    if (value & 0x800000UL) value |= 0xFF000000UL;
    int32_t signedVal = (int32_t)value;
    hxAccum += signedVal;
    hxCount++;
  }

  // Periodically update filtered force (after collecting samples or if timeout)
  if ((hxCount >= HX711_READ_SAMPLES) || (millis() - lastForceUpdateMs > 100)) {
    if (hxCount > 0) {
      int32_t avgRaw = hxAccum / hxCount;
      lastHxRaw = avgRaw;
      
      if (!hx711Tared) { // First time establish tare baseline
        hx711Offset = avgRaw;
        hx711Tared = true;
      }
      
      int32_t diff = avgRaw - hx711Offset;
      float instKg = (hx711ScaleCountsPerKg > 0.0f) ? (diff / hx711ScaleCountsPerKg) : 0.0f;
      
      // IIR filter
      filteredForceKg = FORCE_IIR_ALPHA * instKg + (1.0f - FORCE_IIR_ALPHA) * filteredForceKg;
      lastForceUpdateMs = millis();
    }
    hxAccum = 0;
    hxCount = 0;
  }
}

void tareLoadCell() {
  hx711Offset = lastHxRaw;
  hx711Tared = true;
  Serial.println(F("TARE OK"));
}

void calibrateLoadCell(float knownWeightKg) {
  if (knownWeightKg > 0.0f) {
    int32_t diff = lastHxRaw - hx711Offset;
    hx711ScaleCountsPerKg = diff / knownWeightKg; // counts per kg
    Serial.print(F("CAL OK scale counts/kg="));
    Serial.println(hx711ScaleCountsPerKg, 3);
  } else {
    Serial.println(F("CAL ERR - Weight must be positive"));
  }
}

float getForceKg() {
  return filteredForceKg;
}

int32_t getRawReading() {
  return lastHxRaw;
}

float getScaleFactor() {
  return hx711ScaleCountsPerKg;
}
