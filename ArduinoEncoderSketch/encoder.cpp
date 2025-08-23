#include "encoder.h"

// ====== ENCODER STATE ======
volatile int64_t positionCounts = 0;
volatile int8_t  lastStateAB = 0;
volatile uint32_t lastEdgeMicros = 0;
volatile uint32_t edgeDeltaMicros = 0;
volatile bool indexFlag = false;

float emaCountsPerSec = 0.0f;
int64_t lastSamplePos = 0;

// Transition table for quadrature (old<<2 | new) -> delta
// States: A=(bit1), B=(bit0)
constexpr int8_t quadTable[16] = {
  0,  // 0000 (00->00)
  +1, // 0001 (00->01)
  -1, // 0010 (00->10)
  0,  // 0011 (00->11 invalid skip)
  -1, // 0100 (01->00)
  0,  // 0101 (01->01)
  0,  // 0110 (01->10 invalid)
  +1, // 0111 (01->11)
  +1, // 1000 (10->00)
  0,  // 1001 (10->01 invalid)
  0,  // 1010 (10->10)
  -1, // 1011 (10->11)
  0,  // 1100 (11->00 invalid)
  -1, // 1101 (11->01)
  +1, // 1110 (11->10)
  0   // 1111 (11->11)
};

inline uint32_t micros_fast() {
  return (uint32_t)micros();
}

IRAM_ATTR void updateFromAB() {
  uint8_t a = (uint8_t)digitalRead(ENC_PIN_A);
  uint8_t b = (uint8_t)digitalRead(ENC_PIN_B);
  int8_t newState = (a << 1) | b;
  int idx = ((lastStateAB & 0x3) << 2) | newState;
  int8_t delta = quadTable[idx];
  if (delta) {
    positionCounts += delta;
    uint32_t now = micros_fast();
    edgeDeltaMicros = now - lastEdgeMicros;
    lastEdgeMicros = now;
  }
  lastStateAB = newState;
}

IRAM_ATTR void isrA() { 
  updateFromAB(); 
}

IRAM_ATTR void isrB() { 
  updateFromAB(); 
}

IRAM_ATTR void isrZ() {
#if USE_INDEX
  if (digitalRead(ENC_PIN_Z)) {
    indexFlag = true;
    // Uncomment to zero at index:
    // positionCounts = 0;
  }
#endif
}

void initEncoder() {
  Serial.println(F("Initializing Encoder..."));
  Serial.printf("PPR=%d\n", ENC_PPR);

  // Configure pins
  pinMode(ENC_PIN_A, INPUT_PULLUP);
  pinMode(ENC_PIN_B, INPUT_PULLUP);
#if USE_INDEX
  pinMode(ENC_PIN_Z, INPUT_PULLUP);
#endif

  // Initialize state
  lastStateAB = ((int)digitalRead(ENC_PIN_A) << 1) | (int)digitalRead(ENC_PIN_B);
  lastEdgeMicros = micros_fast();

  // Attach interrupts
  attachInterrupt(digitalPinToInterrupt(ENC_PIN_A), isrA, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_PIN_B), isrB, CHANGE);
#if USE_INDEX
  attachInterrupt(digitalPinToInterrupt(ENC_PIN_Z), isrZ, RISING);
#endif
}

void updateEncoderSpeed(uint32_t currentTime) {
  static uint32_t lastSample = micros_fast();
  
  if ((uint32_t)(currentTime - lastSample) >= SPEED_SAMPLE_US) {
    int64_t pos;
    uint32_t lastEdgeDelta;
    bool zSeen;
    
    // Atomic read of volatile variables
    noInterrupts();
    pos = positionCounts;
    lastEdgeDelta = edgeDeltaMicros;
    zSeen = indexFlag;
    indexFlag = false;
    interrupts();

    // Calculate window-based speed
    int64_t deltaCounts = pos - lastSamplePos;
    lastSamplePos = pos;
    float windowSec = (currentTime - lastSample) / 1e6f;
    float cpsWindow = (windowSec > 0) ? (deltaCounts / windowSec) : 0.0f;

    // Calculate edge-based speed
    float cpsEdge = 0.0f;
    if (lastEdgeDelta > 0) {
      cpsEdge = 1e6f / (float)lastEdgeDelta;
    }

    // Blend both measurements
    float blended = (cpsWindow > 0 && cpsEdge > 0) ? (0.5f * cpsWindow + 0.5f * cpsEdge)
                                                   : (cpsWindow != 0 ? cpsWindow : cpsEdge);

    // Apply EMA filter
    emaCountsPerSec = EMA_ALPHA * blended + (1.0f - EMA_ALPHA) * emaCountsPerSec;

    lastSample = currentTime;
  }
}

float getRPM() {
  float revPerSec = emaCountsPerSec / (float)ENC_PPR;
  return revPerSec * 60.0f;
}

float getRevolutionsPerSecond() {
  return emaCountsPerSec / (float)ENC_PPR;
}

int64_t getPosition() {
  int64_t pos;
  noInterrupts();
  pos = positionCounts;
  interrupts();
  return pos;
}
