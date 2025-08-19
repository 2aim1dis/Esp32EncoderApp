// ESP32-S3 Quadrature Encoder Reader (Omron E6B2-CWZ6C)
// Pins: A=GPIO16 (black), B=GPIO17 (white), Z=GPIO18 (orange, optional)
// Pull-ups: External 4.7k to 3.3V (encoder outputs are open-collector; powered from 5V but logic pulled to 3V3)
// Board (Arduino IDE): ESP32S3 Dev Module (adjust flash/PSRAM as needed)

#include <Arduino.h>

// ====== CONFIG ======
#define ENC_PIN_A    16
#define ENC_PIN_B    17
#define ENC_PIN_Z    18
#define ENC_PPR      1024      // Set to your encoder's pulses per revolution
#define USE_INDEX    1         // 1 = enable Z handling, 0 = disable
#define SPEED_SAMPLE_US 50000  // 50 ms reporting window
#define EMA_ALPHA    0.30f     // 0..1 (higher = more responsive, lower = smoother)

// ====== STATE ======
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

IRAM_ATTR void isrA() { updateFromAB(); }
IRAM_ATTR void isrB() { updateFromAB(); }

IRAM_ATTR void isrZ() {
#if USE_INDEX
  if (digitalRead(ENC_PIN_Z)) {
    indexFlag = true;
    // Uncomment to zero at index:
    // positionCounts = 0;
  }
#endif
}

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println(F("ESP32-S3 Quadrature Encoder Start"));
  Serial.printf("PPR=%d\n", ENC_PPR);

  pinMode(ENC_PIN_A, INPUT_PULLUP);
  pinMode(ENC_PIN_B, INPUT_PULLUP);
#if USE_INDEX
  pinMode(ENC_PIN_Z, INPUT_PULLUP);
#endif

  lastStateAB = ((int)digitalRead(ENC_PIN_A) << 1) | (int)digitalRead(ENC_PIN_B);
  lastEdgeMicros = micros_fast();

  attachInterrupt(digitalPinToInterrupt(ENC_PIN_A), isrA, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_PIN_B), isrB, CHANGE);
#if USE_INDEX
  attachInterrupt(digitalPinToInterrupt(ENC_PIN_Z), isrZ, RISING);
#endif
}

void loop() {
  static uint32_t lastSample = micros_fast();
  uint32_t now = micros_fast();

  if ((uint32_t)(now - lastSample) >= SPEED_SAMPLE_US) {
    int64_t pos;
    uint32_t lastEdgeDelta;
    bool zSeen;
    noInterrupts();
    pos = positionCounts;
    lastEdgeDelta = edgeDeltaMicros;
    zSeen = indexFlag;
    indexFlag = false;
    interrupts();

    int64_t deltaCounts = pos - lastSamplePos;
    lastSamplePos = pos;
    float windowSec = (now - lastSample) / 1e6f;
    float cpsWindow = (windowSec > 0) ? (deltaCounts / windowSec) : 0.0f;

    float cpsEdge = 0.0f;
    if (lastEdgeDelta > 0) {
      cpsEdge = 1e6f / (float)lastEdgeDelta;
    }

    float blended = (cpsWindow > 0 && cpsEdge > 0) ? (0.5f * cpsWindow + 0.5f * cpsEdge)
                                                   : (cpsWindow != 0 ? cpsWindow : cpsEdge);

    emaCountsPerSec = EMA_ALPHA * blended + (1.0f - EMA_ALPHA) * emaCountsPerSec;

    float revPerSec = emaCountsPerSec / (float)ENC_PPR;
    float rpm = revPerSec * 60.0f;

    Serial.printf("Pos=%lld cps=%.1f rpm=%.2f%s\n", (long long)pos, emaCountsPerSec, rpm, zSeen ? " Z" : "");

    lastSample = now;
  }
}
