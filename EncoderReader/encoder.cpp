#include "encoder.h"

// ====== ENCODER STATE ======
volatile int64_t positionCounts = 0;
volatile int8_t  lastStateAB = 0;
volatile uint32_t lastEdgeMicros = 0;
volatile uint32_t edgeDeltaMicros = 0;
volatile bool indexFlag = false;
volatile int8_t lastDeltaSign = 1;  // Sign of last delta (+1 or -1)

float emaCountsPerSec = 0.0f;
int64_t lastSamplePos = 0;

#if USE_HARDWARE_PCNT
pcnt_unit_t pcnt_unit = PCNT_UNIT_0;
int16_t pcnt_overflow_count = 0;
#endif

// Fast GPIO pin masks for direct register access (ESP32-S3)
#define ENC_PIN_A_MASK (1ULL << ENC_PIN_A)
#define ENC_PIN_B_MASK (1ULL << ENC_PIN_B)

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

#if USE_HARDWARE_PCNT

// ====== PCNT IMPLEMENTATION (HIGH PERFORMANCE) ======

IRAM_ATTR void pcnt_overflow_handler(void* arg) {
  pcnt_unit_t unit = (pcnt_unit_t)(uintptr_t)arg;
  
  // Get overflow direction
  uint32_t status = PCNT.int_st.val;
  if (status & (1 << (2 * unit))) {
    pcnt_overflow_count++;  // Positive overflow
  } else if (status & (1 << (2 * unit + 1))) {
    pcnt_overflow_count--;  // Negative overflow
  }
  
  // Clear interrupt
  PCNT.int_clr.val = BIT(unit);
}

void initPCNT() {
  Serial.println(F("Initializing PCNT (Hardware Pulse Counter)..."));
  
  // Configure PCNT unit
  pcnt_config_t pcnt_config = {
    .pulse_gpio_num = ENC_PIN_A,
    .ctrl_gpio_num = ENC_PIN_B,
    .lctrl_mode = PCNT_MODE_REVERSE,  // Reverse when B is low
    .hctrl_mode = PCNT_MODE_KEEP,     // Keep when B is high
    .pos_mode = PCNT_COUNT_INC,       // Increment on positive edge
    .neg_mode = PCNT_COUNT_DIS,       // Disable negative edge counting
    .counter_h_lim = 32767,
    .counter_l_lim = -32768,
    .unit = pcnt_unit,
    .channel = PCNT_CHANNEL_0,
  };
  
  pcnt_unit_config(&pcnt_config);
  
  // Set filter (glitch rejection)
  pcnt_set_filter_value(pcnt_unit, 1000);  // ~1µs filter
  pcnt_filter_enable(pcnt_unit);
  
  // Enable overflow/underflow interrupts
  pcnt_event_enable(pcnt_unit, PCNT_EVT_H_LIM);
  pcnt_event_enable(pcnt_unit, PCNT_EVT_L_LIM);
  
  // Install ISR service and add handler
  pcnt_isr_service_install(ESP_INTR_FLAG_IRAM);
  pcnt_isr_handler_add(pcnt_unit, pcnt_overflow_handler, (void*)pcnt_unit);
  
  // Start counting
  pcnt_counter_clear(pcnt_unit);
  pcnt_counter_resume(pcnt_unit);
}

int64_t readPCNTPosition() {
  int16_t count;
  pcnt_get_counter_value(pcnt_unit, &count);
  
  // Combine overflow count with current count (quadrature = 4x multiplication)
  return ((int64_t)pcnt_overflow_count * 65536LL + count) * 4;
}

void initEncoder() {
  Serial.printf("PPR=%d, Using PCNT Hardware Counter\n", ENC_PPR);
  
  // Initialize pins for PCNT (no pullups needed, handled by PCNT)
  initPCNT();
  
#if USE_INDEX
  // Z pin still needs ISR since PCNT doesn't handle index
  pinMode(ENC_PIN_Z, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENC_PIN_Z), isrZ, RISING);
#endif

  lastEdgeMicros = micros_fast();
}

#else

// ====== OPTIMIZED ISR IMPLEMENTATION ======

IRAM_ATTR void updateFromAB_Fast() {
  uint32_t now = micros_fast();
  
  // Fast GPIO read using direct register access
  uint64_t gpio_in = GPIO.in;
  uint8_t a = (gpio_in & ENC_PIN_A_MASK) ? 1 : 0;
  uint8_t b = (gpio_in & ENC_PIN_B_MASK) ? 1 : 0;
  
  int8_t newState = (a << 1) | b;
  int idx = ((lastStateAB & 0x3) << 2) | newState;
  int8_t delta = quadTable[idx];
  
  if (delta) {
    // Glitch filter - ignore edges too close together
    if ((now - lastEdgeMicros) >= MIN_EDGE_INTERVAL_US) {
      positionCounts += delta;
      edgeDeltaMicros = now - lastEdgeMicros;
      lastEdgeMicros = now;
      lastDeltaSign = (delta > 0) ? 1 : -1;
    }
  }
  lastStateAB = newState;
}

IRAM_ATTR void isrA() { 
  updateFromAB_Fast(); 
}

IRAM_ATTR void isrB() { 
  updateFromAB_Fast(); 
}

void initEncoder() {
  Serial.printf("PPR=%d, Using Optimized ISR\n", ENC_PPR);
  
  // Configure pins
  pinMode(ENC_PIN_A, INPUT_PULLUP);
  pinMode(ENC_PIN_B, INPUT_PULLUP);
  
  // Initialize state with fast GPIO read
  uint64_t gpio_in = GPIO.in;
  uint8_t a = (gpio_in & ENC_PIN_A_MASK) ? 1 : 0;
  uint8_t b = (gpio_in & ENC_PIN_B_MASK) ? 1 : 0;
  lastStateAB = (a << 1) | b;
  lastEdgeMicros = micros_fast();

  // Attach interrupts
  attachInterrupt(digitalPinToInterrupt(ENC_PIN_A), isrA, CHANGE);
  attachInterrupt(digitalPinToInterrupt(ENC_PIN_B), isrB, CHANGE);

#if USE_INDEX
  pinMode(ENC_PIN_Z, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(ENC_PIN_Z), isrZ, RISING);
#endif
}

#endif  // USE_HARDWARE_PCNT

// ====== COMMON FUNCTIONS ======

IRAM_ATTR void isrZ() {
#if USE_INDEX
  if (digitalRead(ENC_PIN_Z)) {
    indexFlag = true;
    // Uncomment to auto-zero at index:
    // positionCounts = 0;
  }
#endif
}

void updateEncoderSpeed(uint32_t currentTime) {
  static uint32_t lastSample = 0;
  
  if (lastSample == 0) lastSample = currentTime;
  
  if ((currentTime - lastSample) >= SPEED_SAMPLE_US) {
    int64_t pos;
    uint32_t lastEdgeDelta;
    int8_t deltaSign;
    bool zSeen;
    
    // Atomic read of volatile variables
    noInterrupts();
#if USE_HARDWARE_PCNT
    pos = readPCNTPosition();
    // For PCNT, we don't have reliable edge timing, so use window-based only
    lastEdgeDelta = 0;  // Force edge calculation to be disabled
    deltaSign = 1;
#else
    pos = positionCounts;
    lastEdgeDelta = edgeDeltaMicros;
    deltaSign = lastDeltaSign;
#endif
    zSeen = indexFlag;
    indexFlag = false;
    interrupts();

    // Calculate window-based speed
    int64_t deltaCounts = pos - lastSamplePos;
    lastSamplePos = pos;
    float windowSec = (currentTime - lastSample) / 1e6f;
    float cpsWindow = (windowSec > 0) ? (deltaCounts / windowSec) : 0.0f;

    // Calculate signed edge-based speed
    float cpsEdge = 0.0f;
#if !USE_HARDWARE_PCNT
    // Only use edge-based calculation when not using PCNT
    if (lastEdgeDelta > 0 && (currentTime - lastEdgeMicros) < VELOCITY_TIMEOUT_US) {
      cpsEdge = (1e6f / (float)lastEdgeDelta) * deltaSign;
    }
#endif

    // Adaptive blending based on velocity magnitude
    float blended;
#if ADAPTIVE_BLENDING && !USE_HARDWARE_PCNT
    float absWindow = abs(cpsWindow);
    float absEdge = abs(cpsEdge);
    
    if (absWindow < 10.0f) {
      // Low speed: prefer window-based
      blended = cpsWindow;
    } else if (absWindow > 1000.0f && absEdge > 0) {
      // High speed: prefer edge-based
      blended = 0.7f * cpsEdge + 0.3f * cpsWindow;
    } else {
      // Medium speed: balanced blend
      blended = (cpsWindow != 0 && cpsEdge != 0) ? (0.5f * cpsWindow + 0.5f * cpsEdge)
                                                  : (cpsWindow != 0 ? cpsWindow : cpsEdge);
    }
#else
    // When using PCNT, use only window-based calculation
    blended = cpsWindow;
#endif

#if !USE_HARDWARE_PCNT
    // Velocity timeout - force to zero if no recent edges (ISR mode only)
    if ((currentTime - lastEdgeMicros) > VELOCITY_TIMEOUT_US) {
      blended = 0.0f;
    }
#endif

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
#if USE_HARDWARE_PCNT
  return readPCNTPosition();
#else
  int64_t pos;
  noInterrupts();
  pos = positionCounts;
  interrupts();
  return pos;
#endif
}

void resetPosition() {
#if USE_HARDWARE_PCNT
  pcnt_counter_clear(pcnt_unit);
  pcnt_overflow_count = 0;
#else
  noInterrupts();
  positionCounts = 0;
  interrupts();
#endif
  lastSamplePos = 0;
}

void setPosition(int64_t newPos) {
#if USE_HARDWARE_PCNT
  // For PCNT, we need to calculate the equivalent counter value
  pcnt_overflow_count = (int16_t)(newPos / (4 * 65536));
  int16_t counterVal = (int16_t)((newPos / 4) % 65536);
  pcnt_counter_clear(pcnt_unit);
  // Note: Setting specific PCNT value is complex, this is a simplified version
#else
  noInterrupts();
  positionCounts = newPos;
  interrupts();
#endif
  lastSamplePos = newPos;
}
