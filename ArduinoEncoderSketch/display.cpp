#include "display.h"
#include "config.h"

void printSystemStatus() {
  Serial.println(F("ESP32-S3 Quadrature Encoder Start"));
  Serial.printf("PPR=%d, Sample Rate=%dms\n", ENC_PPR, SPEED_SAMPLE_US / 1000);
  Serial.printf("LoadCells=%d\n", NUM_LOADCELLS);
  Serial.println(F("Commands: TARE [1|2], CAL <cellIndex> <kg>, RAW, SCALE"));
  Serial.println(F("Output Format: Pos=<position> cps=<counts/sec> rpm=<rpm> force1=<kg> force2=<kg> [Z]"));
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
