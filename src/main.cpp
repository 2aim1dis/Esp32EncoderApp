#include <Arduino.h>
#include "esp_timer.h"
#include "soc/rtc.h"

// Pin assignments
constexpr gpio_num_t PIN_ENC_A = GPIO_NUM_16;
constexpr gpio_num_t PIN_ENC_B = GPIO_NUM_17;
constexpr gpio_num_t PIN_ENC_Z = GPIO_NUM_18; // optional index

// Encoder configuration
constexpr uint32_t PULSES_PER_REV = 1024; // change to match your encoder model
constexpr bool USE_INDEX = true;          // set false if Z not connected

// Speed sample parameters
constexpr uint32_t SPEED_SAMPLE_US = 50000; // 50ms window (20 Hz updates)
constexpr float    EMA_ALPHA = 0.3f;         // smoothing factor for velocity

volatile int32_t positionCounts = 0;        // quadrature position accumulator
volatile int32_t lastEdgeDir = 0;           // last direction (+1/-1)
volatile uint32_t lastEdgeMicros = 0;       // timestamp of last processed edge
volatile uint32_t edgeDeltaMicros = 0;      // delta micros between last two edges
volatile bool indexSeen = false;

// For speed calculation inside loop (copy of volatile vars)
int32_t lastLoopPosition = 0;
float emaCountsPerSec = 0.0f;

IRAM_ATTR void handleQuadratureA();
IRAM_ATTR void handleQuadratureB();
IRAM_ATTR void handleIndexZ();

inline uint32_t micros_fast() {
  return (uint32_t)esp_timer_get_time();
}

IRAM_ATTR void updateQuadrature(bool aState, bool bState) {
  // Standard quadrature direction logic (X4)
  static bool lastA = false, lastB = false;
  // Determine direction from previous state
  int8_t dir = 0;
  if (lastA == aState && lastB == bState) {
    return; // no change
  }
  if (lastA != aState) {
    // A changed
    dir = (aState == bState) ? +1 : -1;
  } else if (lastB != bState) {
    // B changed
    dir = (aState != bState) ? +1 : -1;
  }
  if (dir) {
    positionCounts += dir;
    lastEdgeDir = dir;
    uint32_t now = micros_fast();
    edgeDeltaMicros = now - lastEdgeMicros;
    lastEdgeMicros = now;
  }
  lastA = aState;
  lastB = bState;
}

IRAM_ATTR void handleQuadratureA() {
  bool aState = gpio_get_level(PIN_ENC_A);
  bool bState = gpio_get_level(PIN_ENC_B);
  updateQuadrature(aState, bState);
}
IRAM_ATTR void handleQuadratureB() {
  bool aState = gpio_get_level(PIN_ENC_A);
  bool bState = gpio_get_level(PIN_ENC_B);
  updateQuadrature(aState, bState);
}
IRAM_ATTR void handleIndexZ() {
  if (!USE_INDEX) return;
  if (gpio_get_level(PIN_ENC_Z)) { // rising edge (depends on wiring)
    indexSeen = true;
    // Option 1: Reset position at index:
    // positionCounts = 0;
    // Option 2: Latch position: nothing here.
  }
}

void IRAM_ATTR attachEncoderInterrupts() {
  pinMode(PIN_ENC_A, INPUT_PULLUP);
  pinMode(PIN_ENC_B, INPUT_PULLUP);
  if (USE_INDEX) pinMode(PIN_ENC_Z, INPUT_PULLUP);

  attachInterrupt(digitalPinToInterrupt(PIN_ENC_A), handleQuadratureA, CHANGE);
  attachInterrupt(digitalPinToInterrupt(PIN_ENC_B), handleQuadratureB, CHANGE);
  if (USE_INDEX) attachInterrupt(digitalPinToInterrupt(PIN_ENC_Z), handleIndexZ, RISING);
}

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("ESP32-S3 Quadrature Encoder Init");
  Serial.printf("PPR=%lu\n", (unsigned long)PULSES_PER_REV);
  attachEncoderInterrupts();
  lastEdgeMicros = micros_fast();
}

void loop() {
  static uint32_t lastSpeedSample = micros_fast();
  uint32_t now = micros_fast();
  if (now - lastSpeedSample >= SPEED_SAMPLE_US) {
    noInterrupts();
    int32_t pos = positionCounts;
    uint32_t deltaEdge = edgeDeltaMicros; // time between last 2 edges
    interrupts();

    int32_t deltaCounts = pos - lastLoopPosition;
    lastLoopPosition = pos;

    float windowSec = (now - lastSpeedSample) / 1e6f;
    float instCountsPerSec = deltaCounts / windowSec;

    // Optional refinement: if deltaEdgeMicros valid and small, can estimate peak speed
    if (deltaEdge > 0) {
      float edgeBasedCPS = (1e6f / deltaEdge); // counts per second for single edge spacing
      // Blend edge-based for fast response
      instCountsPerSec = (instCountsPerSec * 0.5f) + (edgeBasedCPS * 0.5f);
    }

    // Exponential smoothing
    emaCountsPerSec = EMA_ALPHA * instCountsPerSec + (1.0f - EMA_ALPHA) * emaCountsPerSec;

    float revPerSec = emaCountsPerSec / (float)PULSES_PER_REV;
    float rpm = revPerSec * 60.0f;

    Serial.printf("Pos=%ld cps=%.1f rpm=%.2f\n", (long)pos, emaCountsPerSec, rpm);

    lastSpeedSample = now;
  }
}
