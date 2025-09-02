# Μάθημα: Κατανοώντας το config.h - Κεντρικές Ρυθμίσεις Συστήματος

## Περιεχόμενα
1. [Τι είναι το config.h;](#1-τι-είναι-το-configh)
2. [Γιατί Χρειαζόμαστε Header Guards;](#2-γιατί-χρειαζόμαστε-header-guards)
3. [Encoder Configuration - Βασικές Ρυθμίσεις](#3-encoder-configuration---βασικές-ρυθμίσεις)
4. [High Performance Configuration - Προχωρημένες Ρυθμίσεις](#4-high-performance-configuration---προχωρημένες-ρυθμίσεις)
5. [Παραδείγματα Προσαρμογής](#5-παραδείγματα-προσαρμογής)
6. [Προχωρημένες Τεχνικές](#6-προχωρημένες-τεχνικές)

---

## 1. Τι είναι το config.h;

### Φιλοσοφία του Configuration File
Το `config.h` είναι το **"κέντρο ελέγχου"** του συστήματός μας. Σκεφτείτε το σαν:

```
┌─────────────────────────────────────┐
│           ΚΕΝΤΡΟ ΕΛΕΓΧΟΥ            │
│  ┌─────────┬─────────┬─────────────┐ │
│  │ Encoder │ Speed   │ Performance │ │
│  │ Settings│Settings │ Tuning      │ │
│  └─────────┴─────────┴─────────────┘ │
│            ↓ ↓ ↓                   │
├─────────────────────────────────────┤
│ encoder.cpp   display.cpp  main.cpp │ ← Όλα διαβάζουν από εδώ
└─────────────────────────────────────┘
```

### Γιατί όχι hardcoded values;
```cpp
// ΚΑΚΗ ΠΡΑΚΤΙΚΗ - Hardcoded values:
void setupEncoder() {
  pinMode(16, INPUT_PULLUP);  // Τι είναι το 16; 🤔
  encoder_ppr = 1024;         // Γιατί 1024; 🤔
  speed_sample = 10000;       // Τι σημαίνει 10000; 🤔
}

// ΚΑΛΗ ΠΡΑΚΤΙΚΗ - Configuration file:
#include "config.h"
void setupEncoder() {
  pinMode(ENC_PIN_A, INPUT_PULLUP);  // Ξεκάθαρο! ✓
  encoder_ppr = ENC_PPR;             // Διαμορφώσιμο! ✓
  speed_sample = SPEED_SAMPLE_US;    // Τεκμηριωμένο! ✓
}
```

---

## 2. Γιατί Χρειαζόμαστε Header Guards;

### Το Πρόβλημα της Multiple Inclusion

```cpp
#ifndef CONFIG_H  // ← "Αν δεν έχεις δει το CONFIG_H πριν..."
#define CONFIG_H  // ← "...μάρκαρε ότι το είδες τώρα"

// Περιεχόμενο αρχείου...

#endif // CONFIG_H  // ← "Τέλος της προστασίας"
```

**Τι συμβαίνει χωρίς Header Guards;**

```cpp
// main.cpp
#include "config.h"     // 1η φορά - OK
#include "encoder.h"    // encoder.h περιέχει #include "config.h" - 2η φορά!

// Αποτέλεσμα χωρίς header guards:
#define ENC_PIN_A 16    // 1η φορά
#define ENC_PIN_A 16    // 2η φορά - ERROR: "redefinition"!
```

**Με Header Guards:**
```cpp
// 1η φορά: CONFIG_H δεν υπάρχει → εκτελείται
// 2η φορά: CONFIG_H υπάρχει → παραλείπεται
```

### Εναλλακτικά: #pragma once

```cpp
// Παλιός τρόπος (portable):
#ifndef CONFIG_H
#define CONFIG_H
// content...
#endif

// Νέος τρόπος (compiler-specific):
#pragma once
// content...
```

**Γιατί επιλέγουμε #ifndef;**
- Portable σε όλους τους compilers ✓
- Explicit και ξεκάθαρο ✓
- Standard C/C++ practice ✓

---

## 3. Encoder Configuration - Βασικές Ρυθμίσεις

### Pin Definitions - Απλές αλλά κρίσιμες

```cpp
#define ENC_PIN_A    16
#define ENC_PIN_B    17
#define ENC_PIN_Z    18
```

**Γιατί #define και όχι const int;**

```cpp
// #define - Preprocessor substitution:
#define ENC_PIN_A 16
pinMode(ENC_PIN_A, INPUT);  // Γίνεται: pinMode(16, INPUT);
// Πλεονεκτήματα:
// ✓ Zero memory footprint
// ✓ Compile-time constant
// ✓ Can be used in array dimensions

// const int - Runtime constant:
const int ENC_PIN_A = 16;
pinMode(ENC_PIN_A, INPUT);  // Memory reference, slower
// Πλεονεκτήματα:
// ✓ Type safety
// ✓ Scope respect
// ✗ Memory usage
```

### Encoder Resolution (PPR) - Η Καρδιά της Ακρίβειας

```cpp
#define ENC_PPR      1024      // Set to your encoder's pulses per revolution
```

**Τι σημαίνει PPR;**

```
Encoder με 1024 PPR:
┌─────────────────────────────────┐
│ Μια πλήρης στροφή (360°)        │
│ = 1024 παλμοί από A             │
│ = 1024 παλμοί από B             │
│ = 4096 quadrature edges         │ ← Αυτό χρησιμοποιούμε!
└─────────────────────────────────┘

Ανάλυση: 360° / 4096 = 0.088° per edge
```

**Παραδείγματα διαφορετικών encoders:**
```cpp
// Cheap encoder:
#define ENC_PPR 20        // 80 edges/rev → 4.5° resolution

// Standard encoder:  
#define ENC_PPR 1024      // 4096 edges/rev → 0.088° resolution

// High-precision encoder:
#define ENC_PPR 5000      // 20000 edges/rev → 0.018° resolution
```

### Index (Z) Channel Configuration

```cpp
#define USE_INDEX    1         // 1 = enable Z handling, 0 = disable
```

**Τι είναι το Index signal;**

```
Κανονικά A/B signals:
A: ■□■□■□■□■□■□■□■□■□■□■□■□■□■□■□■□■□■□
B: □■□■□■□■□■□■□■□■□■□■□■□■□■□■□■□■□■□■

Index (Z): Μία φορά ανά στροφή:
Z: ___________________________■_________________________
                               ↑
                        Absolute reference!
```

**Πότε χρησιμοποιούμε το Index;**
- ✓ **Absolute positioning** - Γνωρίζω την ακριβή θέση
- ✓ **Multi-turn counting** - Μετράω πλήρεις στροφές
- ✓ **Homing sequences** - Αναφορά μηδέν
- ✗ **Simple speed measurement** - Δεν χρειάζεται

### Speed Sampling Window

```cpp
#define SPEED_SAMPLE_US 10000  // 10 ms reporting window (5x faster)
```

**Συνέπειες του Sampling Rate:**

```cpp
// Πολύ αργό sampling (100ms):
#define SPEED_SAMPLE_US 100000
// Αποτέλεσμα: Αργή απόκριση, σταθερές μετρήσεις
// Καλό για: DC motors, slow applications

// Γρήγορο sampling (1ms):
#define SPEED_SAMPLE_US 1000
// Αποτέλεσμα: Γρήγορη απόκριση, θορυβώδεις μετρήσεις
// Καλό για: High-speed servos, real-time control

// Balanced sampling (10ms): ← Η επιλογή μας
#define SPEED_SAMPLE_US 10000
// Αποτέλεσμα: Καλή απόκριση + αποδεκτός θόρυβος
```

**Μαθηματική Ανάλυση:**
```
Sampling Rate = 1 / (10ms) = 100 Hz
Nyquist Frequency = 50 Hz
→ Μπορούμε να detect speed changes μέχρι 50 Hz
→ Για 1000 RPM: 1000/60 = 16.67 Hz ✓ Εντός ορίων!
```

### EMA Alpha - Filtering Intelligence

```cpp
#define EMA_ALPHA    0.40f     // 0..1 (higher = more responsive, lower = smoother)
```

**Exponential Moving Average Theory:**

```
EMA[n] = α × NewValue + (1-α) × EMA[n-1]

α = 0.1 → πολύ smooth, αργή απόκριση
α = 0.5 → balanced
α = 0.9 → γρήγορη απόκριση, λίγο smooth
```

**Παράδειγμα με α=0.4:**
```
Μέτρηση 1: 1000 cps → EMA = 0.4×1000 + 0.6×0     = 400 cps
Μέτρηση 2: 1100 cps → EMA = 0.4×1100 + 0.6×400   = 680 cps  
Μέτρηση 3: 900 cps  → EMA = 0.4×900  + 0.6×680   = 768 cps
Μέτρηση 4: 900 cps  → EMA = 0.4×900  + 0.6×768   = 821 cps
```

**Time Constant Analysis:**
```cpp
τ = -Δt / ln(1-α)
τ = -10ms / ln(0.6) = 19.5ms

// Σημασία: Το 63% του change γίνεται σε ~20ms
// Πλήρης απόκριση (99%) σε ~5τ = 97ms
```

---

## 4. High Performance Configuration - Προχωρημένες Ρυθμίσεις

### Hardware vs Software - Η Κρίσιμη Απόφαση

```cpp
#define USE_HARDWARE_PCNT  1   // 1 = use ESP32 PCNT peripheral, 0 = use ISR
```

**Performance Analysis:**

```
SOFTWARE ISR MODE:
- Κάθε edge → CPU interrupt
- Context switch overhead: ~5μs
- digitalRead() latency: ~3μs  
- Processing: ~2μs
- Total per edge: ~10μs

Στις 50,000 edges/sec:
CPU Load = 50,000 × 10μs = 500ms/sec = 50% CPU! 😱

HARDWARE PCNT MODE:
- Zero CPU overhead για counting
- Αυτόματη direction detection
- Built-in glitch filtering  
- Hardware overflow handling
- CPU Load ≈ 0% για counting! 😍
```

**Πότε να χρησιμοποιήσουμε κάθε mode;**

```cpp
// High-speed applications (>10,000 edges/sec):
#define USE_HARDWARE_PCNT  1  // Υποχρεωτικό!

// Low-speed applications (<1,000 edges/sec):
#define USE_HARDWARE_PCNT  0  // ISR OK, πιο ευέλικτο

// Debugging/development:
#define USE_HARDWARE_PCNT  0  // Εύκολο debugging
```

### Glitch Filtering - Προστασία από Θόρυβο

```cpp
#define MIN_EDGE_INTERVAL_US 10 // Minimum time between edges to filter glitches
```

**Τι είναι glitch;**

```
Κανονικό σήμα:
A: ___┌─────┐_____┌─────┐_____

Glitch (θόρυβος):  
A: ___┌─┐┌──┐_____┌─────┐_____
      ↑ ↑  False edges από EMI!
```

**Glitch Filter Logic:**
```cpp
void processEdge() {
  uint32_t now = micros();
  if ((now - lastEdgeMicros) >= MIN_EDGE_INTERVAL_US) {
    // Valid edge - process it
    processValidEdge();
  } else {
    // Too soon - probably glitch, ignore
    return;
  }
}
```

**Επιλογή του MIN_EDGE_INTERVAL_US:**

```
Για 10μs minimum:
Maximum frequency = 1 / (2 × 10μs) = 50,000 Hz
Max RPM (1024 PPR) = 50,000 / (4 × 1024) × 60 = 732 RPM

Εάν χρειάζεστε υψηλότερες ταχύτητες:
5μs → 1,465 RPM max
2μs → 3,662 RPM max  
1μs → 7,324 RPM max
```

### Velocity Timeout - Intelligent Zero Detection

```cpp
#define VELOCITY_TIMEOUT_US  500000 // 500ms - zero velocity if no edges
```

**Το Πρόβλημα:**
```cpp
// Χωρίς timeout:
lastMeasuredSpeed = 1000 RPM;
// Motor σταματάει...
// Speed παραμένει 1000 RPM για πάντα! ❌

// Με timeout:
if ((now - lastEdgeMicros) > 500000) {
  speed = 0;  // Αναγκαστικό μηδενισμό ✓
}
```

**Timeout Value Selection:**

```
Για 500ms timeout:
Minimum detectable RPM = 60 / (0.5s × PPR/4)
                       = 60 / (0.5 × 1024/4)
                       = 0.47 RPM

// Αυτό σημαίνει: Εάν ο encoder κάνει <0.47 RPM,
// το σύστημα θα το θεωρήσει σταματημένο
```

**Προσαρμογή ανά εφαρμογή:**
```cpp
// Precision instruments (πολύ αργές κινήσεις):
#define VELOCITY_TIMEOUT_US  2000000  // 2 seconds

// Robotics (γρήγορη απόκριση):  
#define VELOCITY_TIMEOUT_US  100000   // 100ms

// General purpose:
#define VELOCITY_TIMEOUT_US  500000   // 500ms (default)
```

### Adaptive Blending - Έξυπνη Συνδυασμένη Μέτρηση

```cpp
#define ADAPTIVE_BLENDING 1    // 1 = adaptive window/edge blending, 0 = fixed 50/50
```

**Η Θεωρία πίσω από το Blending:**

```
Window Method (Time-based):
+ Σταθερό σε χαμηλές ταχύτητες  
+ Καλό SNR (Signal-to-Noise Ratio)
- Αργή απόκριση σε αλλαγές
- Discretization errors σε χαμηλές ταχύτητες

Edge Method (Period-based):
+ Άμεση απόκριση σε αλλαγές
+ Καλή ανάλυση σε υψηλές ταχύτητες
- Θορυβώδες σε χαμηλές ταχύτητες
- Undefined όταν δεν υπάρχουν edges
```

**Adaptive Algorithm Pseudocode:**

```cpp
if (abs(windowSpeed) < 10.0) {
  // Low speed: Window dominates
  finalSpeed = windowSpeed;
} else if (abs(windowSpeed) > 1000.0 && edgeSpeed != 0) {
  // High speed: Edge dominates  
  finalSpeed = 0.7 * edgeSpeed + 0.3 * windowSpeed;
} else {
  // Medium speed: Balanced
  finalSpeed = 0.5 * (windowSpeed + edgeSpeed);
}
```

**Γιατί αυτά τα thresholds;**

```
10 cps threshold:
- Για 1024 PPR: 10/4096 = 0.0024 rev/s = 0.146 RPM
- Κάτω από αυτό: Πολύ λίγα edges για αξιόπιστο edge measurement

1000 cps threshold:  
- Για 1024 PPR: 1000/4096 = 0.244 rev/s = 14.6 RPM
- Πάνω από αυτό: Window method έχει μεγάλη καθυστέρηση
```

---

## 5. Παραδείγματα Προσαρμογής

### Σενάριο 1: CNC Machine (High Precision)

```cpp
// CNC_config.h
#define ENC_PIN_A    16
#define ENC_PIN_B    17  
#define ENC_PIN_Z    18
#define ENC_PPR      5000        // High-resolution encoder
#define USE_INDEX    1           // Absolute positioning critical
#define SPEED_SAMPLE_US 5000     // 5ms για γρήγορη response
#define EMA_ALPHA    0.30f       // Πιο smooth για precision
#define USE_HARDWARE_PCNT  1     // Υποχρεωτικό για high PPR
#define MIN_EDGE_INTERVAL_US 2   // High-speed capability
#define VELOCITY_TIMEOUT_US  100000  // 100ms γρήγορο stop detection
#define ADAPTIVE_BLENDING 1      // Βέλτιστη απόδοση
```

### Σενάριο 2: Slow Motor Control

```cpp
// SlowMotor_config.h  
#define ENC_PIN_A    16
#define ENC_PIN_B    17
#define ENC_PIN_Z    18
#define ENC_PPR      100         // Χαμηλό resolution OK
#define USE_INDEX    0           // Δεν χρειάζεται
#define SPEED_SAMPLE_US 50000    // 50ms slow sampling
#define EMA_ALPHA    0.60f       // Πιο responsive
#define USE_HARDWARE_PCNT  0     // ISR mode OK για χαμηλές ταχύτητες
#define MIN_EDGE_INTERVAL_US 100 // Aggressive glitch filtering
#define VELOCITY_TIMEOUT_US  2000000  // 2s για πολύ αργές κινήσεις
#define ADAPTIVE_BLENDING 0      // Fixed blending OK
```

### Σενάριο 3: Educational/Debugging

```cpp
// Debug_config.h
#define ENC_PIN_A    16  
#define ENC_PIN_B    17
#define ENC_PIN_Z    18
#define ENC_PPR      20          // Χαμηλό για εύκολο debugging
#define USE_INDEX    1           // Test όλες τις λειτουργίες  
#define SPEED_SAMPLE_US 100000   // 100ms για readable output
#define EMA_ALPHA    0.80f       // Gyros για να βλέπω αλλαγές
#define USE_HARDWARE_PCNT  0     // ISR για debugging visibility
#define MIN_EDGE_INTERVAL_US 0   // No filtering για debugging
#define VELOCITY_TIMEOUT_US  1000000  // 1s
#define ADAPTIVE_BLENDING 0      // Απλοποιημένη λογική
```

---

## 6. Προχωρημένες Τεχνικές

### Conditional Compilation Mastery

**Advanced Preprocessing:**
```cpp
// Automatic pin validation:
#if (ENC_PIN_A < 0) || (ENC_PIN_A > 39)
  #error "ENC_PIN_A must be between 0-39 for ESP32"
#endif

// Performance warnings:
#if (ENC_PPR > 2000) && (USE_HARDWARE_PCNT == 0)
  #warning "High PPR with ISR mode - consider USE_HARDWARE_PCNT=1"
#endif

// Feature dependencies:
#if USE_INDEX && !defined(ENC_PIN_Z)  
  #error "USE_INDEX requires ENC_PIN_Z to be defined"
#endif
```

### Runtime vs Compile-time Configuration

```cpp
// Compile-time (current approach):
#define SPEED_SAMPLE_US 10000
// Advantages: Zero runtime overhead, compiler optimization
// Disadvantages: Must recompile to change

// Runtime alternative:
extern uint32_t speedSampleUs;  // in .cpp: uint32_t speedSampleUs = 10000;
// Advantages: Can change during runtime, EEPROM storage possible
// Disadvantages: Memory usage, slower access
```

### Template-based Configuration (Advanced C++)

```cpp
// Advanced: Template-based configuration
template<int PPR, bool USE_PCNT, uint32_t SAMPLE_US>
class EncoderConfig {
  static constexpr int enc_ppr = PPR;
  static constexpr bool use_pcnt = USE_PCNT;
  static constexpr uint32_t sample_us = SAMPLE_US;
  
  // Compile-time validation:
  static_assert(PPR > 0, "PPR must be positive");
  static_assert(SAMPLE_US >= 1000, "Sample rate too high");
};

// Usage:
using MyConfig = EncoderConfig<1024, true, 10000>;
```

### Configuration Profiles

```cpp
// config_profiles.h
#ifdef PROFILE_CNC
  #define ENC_PPR      5000
  #define SPEED_SAMPLE_US 5000  
  #define EMA_ALPHA    0.30f
#elif defined(PROFILE_ROBOTICS)
  #define ENC_PPR      1024
  #define SPEED_SAMPLE_US 10000
  #define EMA_ALPHA    0.40f  
#elif defined(PROFILE_SLOW_MOTOR)
  #define ENC_PPR      100
  #define SPEED_SAMPLE_US 50000
  #define EMA_ALPHA    0.60f
#else
  #define ENC_PPR      1024  // Default profile
  #define SPEED_SAMPLE_US 10000
  #define EMA_ALPHA    0.40f
#endif

// Compilation: gcc -DPROFILE_CNC main.cpp
```

---

## Συμπέρασμα: Η Δύναμη της Proper Configuration

Το `config.h` αρχείο είναι **πολύ περισσότερο** από απλές σταθερές. Είναι:

### 🎯 **Strategic Design Tool**
- Κεντρικός έλεγχος όλων των παραμέτρων
- Εύκολη προσαρμογή για διαφορετικές εφαρμογές
- Validation και error checking στο compile time

### ⚡ **Performance Engineering**
- Hardware vs software trade-offs
- Memory vs speed optimizations  
- Real-time vs precision balance

### 🧠 **Intelligent Configuration**
- Adaptive algorithms με configurable thresholds
- Profile-based setups
- Advanced preprocessing techniques

### 🛡️ **Robust Engineering**
- Glitch filtering configuration
- Timeout management
- Error prevention through validation

Η σωστή διαμόρφωση του `config.h` είναι η διαφορά μεταξύ ενός **amateur project** και ενός **professional embedded system**. Κάθε παράμετρος έχει σκεφτεί προσεκτικά για να παρέχει τον καλύτερο συμβιβασμό μεταξύ απόδοσης, ακρίβειας, και αξιοπιστίας.

**Θυμηθείτε:** Το καλό configuration είναι αυτό που **δεν χρειάζεται να αλλάξει** όταν αλλάζουν οι απαιτήσεις - απλώς προσαρμόζεται με διαφορετικές τιμές! 🎉
