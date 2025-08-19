// ESP32-S3 Quadrature Encoder + HX711 Load Cell (Omron E6B2-CWZ6C + LP7145 via HX711)
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

// Enable extra HX711 debug output (set to 1 to print raw/adjusted readings periodically)
#define HX711_DEBUG 1

// HX711 pins (ESP32-S3 GPIO numbers)
#define HX711_DOUT  40  // Data pin
#define HX711_SCK   41  // Clock pin

// --- Load Cell Calibration Data (LP7145C certificate) ---
// Capacity (Emax): 300 kg
// Accuracy Class: C3
// Rated Output (R.O.): 1.2 ±0.1 mV/V at full scale (300 kg)
// Input / Output impedance: 1000 ±10 Ω
// Serial: 21100002
#define LOAD_CELL_CAPACITY_KG        300.0f
#define LOAD_CELL_RATED_OUTPUT_MV_V  1.2f      // mV per Volt at full scale
#define LOAD_CELL_CLASS              "C3"
#define LOAD_CELL_SERIAL             "21100002"
// Set this to the actual excitation voltage your HX711 module applies to the load cell (typically 5.0V, sometimes 4.3-4.9V, or 3.3V if modified)
#define LOAD_CELL_EXCITATION_V       5.0f
// HX711 nominal full-scale differential input at gain 128 is about ±20 mV
#define HX711_FULL_SCALE_MV          20.0f

// Filtering / oversampling parameters for load cell
#define HX711_AVG_SAMPLES    8      // raw reads per displayed force update
#define FORCE_LP_ALPHA       0.20f  // IIR low-pass (0..1)
#define CAL_SAMPLES          40     // raw samples for calibration measurement

// Load cell calibration
// Raw HX711 reading at zero (tare) and scale factor (raw units per kg) - set after calibration
static long hx711_offset = 0;       // determined with tare
static float hx711_scale = 1000.0f; // will be recomputed from certificate data (approx) then can be fine-tuned
static long hx711_last_raw = 0;      // last raw reading captured
static float force_filtered_kg = 0.0f; // low-pass filtered force

// Simple HX711 bit-bang (blocking, not for highest sample rates but ok for ~10-80 SPS)
long readHX711()
{
  // Wait for chip ready (DOUT goes LOW)
  uint32_t start = micros();
  while (digitalRead(HX711_DOUT) == HIGH) {
    if (micros() - start > 1000000UL) return 0; // timeout 1s
  }
  unsigned long value = 0;
  // 24 bits
  for (int i = 0; i < 24; i++) {
    digitalWrite(HX711_SCK, HIGH);
    delayMicroseconds(1);
    value = (value << 1) | (digitalRead(HX711_DOUT) & 0x1);
    digitalWrite(HX711_SCK, LOW);
    delayMicroseconds(1);
  }
  // Set gain channel A 128 by 1 extra pulse
  digitalWrite(HX711_SCK, HIGH); delayMicroseconds(1); digitalWrite(HX711_SCK, LOW); delayMicroseconds(1);
  // Sign extend 24-bit two's complement
  if (value & 0x800000UL) value |= 0xFF000000UL;
  return (long)value;
}

float getLoadKg()
{
  // Oversample
  long sum = 0;
  for (int i=0;i<HX711_AVG_SAMPLES;i++) {
    long r = readHX711();
    sum += r;
  }
  long raw = sum / HX711_AVG_SAMPLES;
  hx711_last_raw = raw;
  long adj = raw - hx711_offset;
  float instKg = adj / hx711_scale;
  // Low-pass filter
  force_filtered_kg = force_filtered_kg + FORCE_LP_ALPHA * (instKg - force_filtered_kg);
  return force_filtered_kg;
}
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
  Serial.println(F("ESP32-S3 Quadrature Encoder + HX711 Start"));
  Serial.printf("PPR=%d\n", ENC_PPR);

  pinMode(HX711_SCK, OUTPUT);
  pinMode(HX711_DOUT, INPUT);
  digitalWrite(HX711_SCK, LOW);

  // Tare: take several samples
  long sum = 0; int n = 10;
  for (int i=0;i<n;i++){ sum += readHX711(); }
  hx711_offset = sum / n;
  Serial.printf("HX711 tare offset=%ld\n", hx711_offset);
  // Approximate scale from certificate:
  // Expected full-scale mV = R.O. * excitation_V
  float rated_mV = LOAD_CELL_RATED_OUTPUT_MV_V * LOAD_CELL_EXCITATION_V;
  float fractionFS = rated_mV / HX711_FULL_SCALE_MV; // fraction of HX711 full-scale range
  if (fractionFS > 1.0f) fractionFS = 1.0f;
  float expected_counts = fractionFS * 8388607.0f; // 2^23 - 1 positive span
  hx711_scale = expected_counts / LOAD_CELL_CAPACITY_KG; // raw units per kg
  Serial.printf("HX711 computed scale=%.1f raw units/kg (excitation=%.2fV, rated_mV=%.3f, countsFS=%.0f)\n",
                hx711_scale, LOAD_CELL_EXCITATION_V, rated_mV, expected_counts);
  Serial.println(F("NOTE: For higher accuracy, place a known weight W, read raw delta = readHX711()-offset, then hx711_scale = delta / W."));

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

  // Simple serial command interface for calibration (send lines like: TARE or CAL 10.0 )
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    if (cmd.equalsIgnoreCase("TARE")) {
      long sum=0; int n=25; for(int i=0;i<n;i++){ sum += readHX711(); delay(40);} hx711_offset = sum / n; force_filtered_kg = 0; Serial.printf("[TARE] New offset=%ld\n", hx711_offset);
    } else if (cmd.startsWith("CAL ")) {
      float known= cmd.substring(4).toFloat();
      if (known > 0.01f) {
        // Collect raw adjusted samples
        long vals[CAL_SAMPLES];
        for(int i=0;i<CAL_SAMPLES;i++){ long r=readHX711(); vals[i] = (r - hx711_offset); delay(30);} 
        // Simple insertion sort (CAL_SAMPLES small)
        for(int i=1;i<CAL_SAMPLES;i++){ long key=vals[i]; int j=i-1; while(j>=0 && vals[j]>key){ vals[j+1]=vals[j]; j--; } vals[j+1]=key; }
        int trim = CAL_SAMPLES/10; // trim 10% on each side
        if (trim > 3) trim = 3; // limit
        long sumAdj = 0; int count=0;
        for(int i=trim;i<CAL_SAMPLES-trim;i++){ sumAdj += vals[i]; count++; }
        long trimmedMean = sumAdj / (count?count:1);
        hx711_scale = (float)trimmedMean / known; force_filtered_kg = 0;
        Serial.printf("[CAL] trimmedMean=%ld known=%.3fkg -> hx711_scale=%.3f raw/kg (removed %d each side)\n", trimmedMean, known, hx711_scale, trim);
      } else {
        Serial.println(F("[CAL] Provide positive weight in kg, e.g. 'CAL 5.00'"));
      }
    } else if (cmd.equalsIgnoreCase("RAW")) {
      long r = readHX711(); Serial.printf("[RAW] %ld (offset %ld, adj %ld)\n", r, hx711_offset, r - hx711_offset);
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

    float forceKg = getLoadKg();
    Serial.printf("Pos=%lld cps=%.1f rpm=%.2f force=%.3fkg%s\n", (long long)pos, emaCountsPerSec, rpm, forceKg, zSeen ? " Z" : "");
#if HX711_DEBUG
    static uint32_t lastDbg = 0;
    if ((now - lastDbg) > 1000000UL) { // every ~1s
      long adj = hx711_last_raw - hx711_offset;
      float inst = (float)adj / hx711_scale;
      Serial.printf("[HX711] raw=%ld offset=%ld adj=%ld scale=%.3f inst=%.4fkg filt=%.4fkg\n", hx711_last_raw, hx711_offset, adj, hx711_scale, inst, force_filtered_kg);
      lastDbg = now;
    }
#endif

    lastSample = now;
  }
}
