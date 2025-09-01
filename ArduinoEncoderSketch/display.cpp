#include "display.h"
#include "config.h"

void printSystemStatus() {
  Serial.println(F("ESP32-S3 High-Performance Quadrature Encoder"));
  Serial.printf("PPR=%d, Sample Rate=%dms\n", ENC_PPR, SPEED_SAMPLE_US / 1000);
  
#if USE_HARDWARE_PCNT
  Serial.println(F("Mode: Hardware PCNT (Maximum Performance)"));
#else
  Serial.println(F("Mode: Optimized ISR"));
#endif

#if ADAPTIVE_BLENDING
  Serial.println(F("Velocity: Adaptive Window/Edge Blending"));
#else
  Serial.println(F("Velocity: Fixed 50/50 Blending"));
#endif

  Serial.printf("Glitch Filter: %d microseconds\n", MIN_EDGE_INTERVAL_US);
  Serial.printf("Velocity Timeout: %d ms\n", VELOCITY_TIMEOUT_US / 1000);
  
  Serial.println(F("Commands: TARE, CAL <kg>, RAW, SCALE, ZERO"));
  Serial.println(F("Output Format: Pos=<position> cps=<counts/sec> rpm=<rpm> force=<kg> [Z]"));
  Serial.println();
}

void printEncoderData(int64_t position, float rpm, float countsPerSec, bool indexSeen) {
  Serial.printf("Pos=%lld cps=%.1f rpm=%.2f", 
                (long long)position, countsPerSec, rpm);
  if (indexSeen) {
    Serial.print(" Z");
  }
}

void printForceData(float forceKg) {
  Serial.printf(" force=%.3fkg\n", forceKg);
  // Optional separate force line for GUI parsers:
  Serial.printf("Force=%.3fkg\n", forceKg);
}
