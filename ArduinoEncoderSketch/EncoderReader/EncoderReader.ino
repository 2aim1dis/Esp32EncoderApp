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

// ====== LOAD CELL / HX711 CONFIG (LP7145C 300kg) ======
#define HX711_DOUT_PIN   40   // Data pin (DOUT)
#define HX711_SCK_PIN    41   // Clock pin (SCK)
#define HX711_READ_SAMPLES 8  // Oversampling per report window
#define FORCE_IIR_ALPHA  0.15f // Low-pass for force (0..1)

// Initial scale: counts per kg (placeholder). Will be replaced by CAL command.
// After calibration: scale = (raw - offset) / known_weight_kg
static float hx711ScaleCountsPerKg = 1000.0f; // UPDATE after CAL
static int32_t hx711Offset = 0;               // Tare offset
static bool hx711Tared = false;
static float filteredForceKg = 0.0f;
static int32_t lastHxRaw = 0;                 // last averaged raw
static uint32_t lastForceUpdateMs = 0;

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

  // HX711 pins
  pinMode(HX711_SCK_PIN, OUTPUT);
  pinMode(HX711_DOUT_PIN, INPUT); // DOUT floats high until data ready (goes LOW)

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

  // ---- Non-blocking HX711 sampling (collect up to HX711_READ_SAMPLES each loop batch) ----
  // HX711 data ready when DOUT LOW.
  static int32_t hxAccum = 0;
  static uint8_t hxCount = 0;
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

  // ---- Command handling (serial) ----
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.equalsIgnoreCase("TARE")) {
      hx711Offset = lastHxRaw;
      hx711Tared = true;
      Serial.println(F("TARE OK"));
    } else if (cmd.startsWith("CAL")) {
      // Format: CAL 10.0  (known weight in kg currently applied)
      int spaceIdx = cmd.indexOf(' ');
      if (spaceIdx > 0) {
        float known = cmd.substring(spaceIdx + 1).toFloat();
        if (known > 0.0f) {
          int32_t diff = lastHxRaw - hx711Offset;
          hx711ScaleCountsPerKg = diff / known; // counts per kg
          Serial.print(F("CAL OK scale counts/kg="));
          Serial.println(hx711ScaleCountsPerKg, 3);
        } else {
          Serial.println(F("CAL ERR"));
        }
      } else {
        Serial.println(F("CAL usage: CAL <kg>"));
      }
    } else if (cmd.equalsIgnoreCase("RAW")) {
      Serial.print(F("RAW=")); Serial.println(lastHxRaw);
    } else if (cmd.equalsIgnoreCase("SCALE")) {
      Serial.print(F("SCALE=")); Serial.println(hx711ScaleCountsPerKg, 6);
    }
  }

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

  Serial.printf("Pos=%lld cps=%.1f rpm=%.2f force=%.3fkg%s\n", (long long)pos, emaCountsPerSec, rpm, filteredForceKg, zSeen ? " Z" : "");
  // Optional separate force line for GUI parsers:
  Serial.printf("Force=%.3fkg\n", filteredForceKg);

    lastSample = now;
  }
}
