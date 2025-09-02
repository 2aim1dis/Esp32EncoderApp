// demo_trace.ino
// Purpose: small demo that prints internal encoder variables each speed window.
// This sketch expects the main encoder code (positionCounts, lastEdgeDelta, etc.)
// to be present in the build (declared as extern here). Use this for runtime tracing.

#include <Arduino.h>

// externs - provided by encoder core (encoder.cpp)
extern volatile int64_t positionCounts;
extern volatile uint32_t lastEdgeDelta; // μs
extern volatile int8_t lastDeltaSign;
extern float emaCountsPerSec;
extern int64_t lastWindowPos;
extern uint32_t lastWindowTime;
extern const uint32_t SPEED_SAMPLE_US;
extern const int countsPerRev;

void setup() {
  Serial.begin(115200);
  while (!Serial) { delay(10); }
  Serial.println(F("=== Encoder demo_trace starting ==="));
}

void loop() {
  uint32_t now = micros();
  if ((now - lastWindowTime) >= SPEED_SAMPLE_US) {
    noInterrupts();
    int64_t posNow = positionCounts; // atomic read
    uint32_t edge_us = lastEdgeDelta;
    int8_t sign = lastDeltaSign;
    interrupts();

    int64_t deltaCounts = posNow - lastWindowPos;
    float windowSec = (now - lastWindowTime) / 1e6f;
    float cpsWindow = (windowSec > 0.0f) ? (deltaCounts / windowSec) : 0.0f;
    float cpsEdge = 0.0f;
    if (edge_us > 0) cpsEdge = 1e6f / (float)edge_us * (float)sign;

    // blending logic (same as firmware)
    float absW = fabsf(cpsWindow);
    float absE = fabsf(cpsEdge);
    float blended;
    if (absW < 10.0f) {
      blended = cpsWindow;
    } else if (absW > 1000.0f && absE > 0.0f) {
      blended = 0.7f * cpsEdge + 0.3f * cpsWindow;
    } else {
      if (absE > 0.0f) blended = 0.5f * (cpsWindow + cpsEdge);
      else blended = cpsWindow;
    }

    // Print internal trace (CSV-like)
    Serial.printf("TRACE time_us=%lu pos=%lld delta=%lld edge_us=%u cpsWindow=%.1f cpsEdge=%.1f blended=%.1f ema=%.1f\n",
                  (unsigned long)now, (long long)posNow, (long long)deltaCounts, (unsigned)edge_us, cpsWindow, cpsEdge, blended, emaCountsPerSec);

    // Update window markers (match main loop behavior)
    lastWindowPos = posNow;
    lastWindowTime = now;
  }
  delay(1);
}
