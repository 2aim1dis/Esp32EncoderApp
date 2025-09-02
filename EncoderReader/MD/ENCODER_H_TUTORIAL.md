# Μάθημα: Κατανοώντας το encoder.h - Header Interface & Architecture

## Περιεχόμενα
1. [Τι είναι το encoder.h;](#1-τι-είναι-το-encoderh)
2. [Header Guards & Includes](#2-header-guards--includes)
3. [Conditional Compilation Strategy](#3-conditional-compilation-strategy)
4. [Global State Variables - Volatile & Threading](#4-global-state-variables---volatile--threading)
5. [Function Declarations - Interface Design](#5-function-declarations---interface-design)
6. [Hardware Abstraction Layer](#6-hardware-abstraction-layer)
7. [Memory Layout & Performance](#7-memory-layout--performance)
8. [Advanced Header Techniques](#8-advanced-header-techniques)

---

## 1. Τι είναι το encoder.h;

### Interface vs Implementation Philosophy

Το `encoder.h` είναι το **"συμβόλαιο"** (contract) του encoder subsystem:

```
┌─────────────────────────────────────────┐
│            ENCODER.H                    │
│         (Interface Layer)               │
├─────────────────────────────────────────┤
│ • Function Declarations                 │  ← "Τι μπορώ να κάνω;"
│ • Data Structure Definitions            │  ← "Τι δεδομένα υπάρχουν;"  
│ • Constants & Types                     │  ← "Τι τύποι χρησιμοποιώ;"
│ • Conditional Compilation               │  ← "Τι variations υπάρχουν;"
└─────────────────────────────────────────┘
            ↓ ↓ ↓ ↓ ↓
┌─────────────────────────────────────────┐
│          ENCODER.CPP                    │
│       (Implementation Layer)           │  ← "Πώς το κάνω πραγματικά;"
└─────────────────────────────────────────┘
```

**Γιατί χωρίζουμε Header από Implementation;**

```cpp
// ❌ Χωρίς headers - Όλα σε ένα αρχείο:
void main() {
  // 500 lines of encoder implementation here
  // 300 lines of display code here  
  // 200 lines of command parsing here
  // TOTAL CHAOS! Cannot reuse, debug, or understand!
}

// ✅ Με headers - Modular design:
#include "encoder.h"    // Interface only - clean!
void main() {
  initEncoder();        // Simple call - implementation hidden
  float rpm = getRPM(); // Clean API - easy to understand
}
```

---

## 2. Header Guards & Includes

### Standard Header Guard Pattern

```cpp
#ifndef ENCODER_H    // ← "Αν δεν έχει οριστεί το ENCODER_H..."
#define ENCODER_H    // ← "...όρισε το τώρα"

// Header content here...

#endif // ENCODER_H  // ← "Τέλος conditional block"
```

**Γιατί όχι #pragma once;**
```cpp
// Modern alternative:
#pragma once

// Issues:
// ❌ Not all compilers support it
// ❌ Can have issues with symbolic links
// ❌ Less explicit than traditional guards
// ✅ But: Cleaner syntax, impossible to get name conflicts
```

### Smart Include Strategy

```cpp
#include <Arduino.h>  // ← System include (angle brackets)
#include "config.h"   // ← Local include (quotes)

#if USE_HARDWARE_PCNT
#include "driver/pcnt.h"      // ← ESP-IDF driver (conditional)
#include "soc/gpio_struct.h"  // ← Direct register access
#endif
```

**Include Order Significance:**

```cpp
// 1. System headers first
#include <Arduino.h>
#include <stdint.h>

// 2. Third-party libraries  
#include "driver/pcnt.h"

// 3. Our project headers (dependency order)
#include "config.h"      // ← Needed by encoder.h
#include "encoder.h"     // ← Can use config definitions

// Why this order?
// - System headers define basic types (uint32_t, etc.)
// - Our headers depend on system definitions
// - Dependency chain must be respected
```

**Conditional Include Analysis:**
```cpp
#if USE_HARDWARE_PCNT
#include "driver/pcnt.h"
#include "soc/gpio_struct.h"
#endif

// This is powerful because:
// ✓ Code compiles with OR without PCNT support
// ✓ Smaller binary when PCNT disabled
// ✓ No wasted flash space for unused drivers
// ✓ Portable across different ESP32 variants
```

---

## 3. Conditional Compilation Strategy

### The Power of #if Preprocessor

```cpp
#if USE_HARDWARE_PCNT
// PCNT-specific declarations
extern pcnt_unit_t pcnt_unit;
extern int16_t pcnt_overflow_count;
#endif
```

**Preprocessor vs Runtime Conditionals:**

```cpp
// ❌ Runtime conditional (always compiled, wastes space):
void initEncoder() {
  if (USE_HARDWARE_PCNT) {
    // PCNT code here - compiled even if never used!
  } else {
    // ISR code here - compiled even if never used!  
  }
  // Both code paths present in binary = larger size
}

// ✅ Preprocessor conditional (compile-time choice):
void initEncoder() {
#if USE_HARDWARE_PCNT
  // Only PCNT code compiled
#else  
  // Only ISR code compiled
#endif
  // Binary contains only the chosen path = smaller size
}
```

**Memory Impact Analysis:**
```
With runtime conditionals:
PCNT code:     2.5KB flash
ISR code:      1.8KB flash  
Total:         4.3KB flash (both paths)

With preprocessor conditionals:
PCNT mode:     2.5KB flash (only PCNT path)
ISR mode:      1.8KB flash (only ISR path)
Savings:       ~41% flash space!
```

### Advanced Conditional Patterns

```cpp
// Feature-based conditionals:
#if USE_HARDWARE_PCNT
  void initPCNT();
  int64_t readPCNTPosition();
#else
  IRAM_ATTR void isrA();
  IRAM_ATTR void isrB(); 
#endif

// Common interface (always available):
void initEncoder();         // ← Works in both modes
int64_t getPosition();      // ← Abstracted implementation
float getRPM();            // ← Mode-independent
```

---

## 4. Global State Variables - Volatile & Threading

### Understanding Volatile Keyword

```cpp
extern volatile int64_t positionCounts;
extern volatile int8_t  lastStateAB;
extern volatile uint32_t lastEdgeMicros;
```

**Τι σημαίνει `volatile`;**

```cpp
// ❌ Χωρίς volatile - Compiler optimization problem:
int64_t position = 0;

void loop() {
  Serial.println(position);  // Compiler: "position never changes in this function"
  delay(100);
  Serial.println(position);  // Compiler: "I can optimize this to same value!"
}

void IRAM_ATTR encoder_isr() {
  position++;  // This changes position, but compiler doesn't know!
}

// Optimized assembly might be:
// load position once, print it twice!
```

```cpp
// ✅ Με volatile - Correct behavior:
volatile int64_t position = 0;

void loop() {
  Serial.println(position);  // Compiler: "Must read from memory"
  delay(100);
  Serial.println(position);  // Compiler: "Must read again, might have changed"
}

// Compiler generates:
// Read from memory location each time
```

**Volatile Rules:**
1. **ISR-modified variables** → Must be volatile
2. **Memory-mapped registers** → Must be volatile  
3. **Multi-threading shared data** → Must be volatile
4. **Hardware-modified values** → Must be volatile

### Threading & Atomic Operations

```cpp
extern volatile bool indexFlag;
extern volatile int8_t lastDeltaSign;
```

**The Race Condition Problem:**

```cpp
// 🚫 Race condition example:
volatile int64_t position = 0;

// Main thread:
void printPosition() {
  int64_t pos = position;  // Read 1: Lower 32 bits
  // ⚡ INTERRUPT HAPPENS HERE - position changes!
  // Read 2: Upper 32 bits (from NEW value!)
  Serial.println(pos);     // Mixed old/new = garbage!
}

// ISR:
IRAM_ATTR void encoder_isr() {
  position += 1;  // 64-bit increment is NOT atomic on 32-bit MCU!
}
```

**Solution - Atomic Reading:**
```cpp
int64_t getPosition() {
  int64_t pos;
  noInterrupts();      // Disable interrupts
  pos = positionCounts; // Atomic read
  interrupts();        // Re-enable interrupts
  return pos;
}
```

### Global vs Local Trade-offs

**Why Global State Variables?**

```cpp
// ✅ Global approach (our choice):
volatile int64_t positionCounts;  // Shared state

IRAM_ATTR void encoder_isr() {
  positionCounts++;  // Direct access - fast!
}

float getRPM() {
  int64_t pos = getPosition();  // Access global state
  // Calculate RPM...
}
```

```cpp
// ❌ Local/encapsulated approach:
class Encoder {
private:
  volatile int64_t position;  // Encapsulated
  
public:  
  IRAM_ATTR void isr() {
    position++;  // Method call overhead in ISR!
  }
};

// Problem: ISR performance penalty, complexity
```

**Trade-off Analysis:**
```
Global State Approach:
✅ Fast ISR performance
✅ Simple embedded design  
✅ Zero memory overhead
❌ Less encapsulation
❌ Potential naming conflicts

OOP Approach:
✅ Better encapsulation
✅ No global namespace pollution
❌ ISR performance penalty
❌ Memory overhead (vtables, etc.)
❌ Complexity in embedded context
```

---

## 5. Function Declarations - Interface Design

### Core Interface Functions

```cpp
void initEncoder();
void updateEncoderSpeed(uint32_t currentTime);
float getRPM();
float getRevolutionsPerSecond();
int64_t getPosition();
void resetPosition();
void setPosition(int64_t newPos);
```

**API Design Principles:**

### 1. Clear Naming Convention
```cpp
// ✅ Good naming:
void initEncoder();        // init + Module + specific action
float getRPM();           // get + specific measurement + units  
void resetPosition();     // action + target

// ❌ Poor naming:
void setup();            // Too generic - setup what?
float speed();           // Units unclear - RPM? cps? m/s?
void zero();            // Zero what? position? speed?
```

### 2. Consistent Return Types
```cpp
// Position functions - all return int64_t:
int64_t getPosition();      // Current absolute position
void setPosition(int64_t);  // Set absolute position  

// Speed functions - all return float:
float getRPM();                    // Revolutions per minute
float getRevolutionsPerSecond();   // Revolutions per second
```

### 3. Side Effect Documentation
```cpp
// Functions with side effects (modify global state):
void initEncoder();              // Modifies: hardware registers, global variables
void updateEncoderSpeed();       // Modifies: emaCountsPerSec, lastSamplePos
void resetPosition();           // Modifies: positionCounts, internal state

// Pure functions (no side effects):  
float getRPM();                 // Only reads global state
int64_t getPosition();          // Only reads global state
```

### Conditional Function Declarations

```cpp
#if USE_HARDWARE_PCNT
void initPCNT();
int64_t readPCNTPosition();
IRAM_ATTR void pcnt_overflow_handler(void* arg);
#else
IRAM_ATTR void isrA();
IRAM_ATTR void isrB();
IRAM_ATTR void updateFromAB_Fast();
#endif
```

**Why Conditional Declarations?**

```cpp
// Scenario: Compiling with USE_HARDWARE_PCNT = 0

// ❌ If we declared both sets always:
void initPCNT();        // Declared but no implementation! 
IRAM_ATTR void isrA();  // This one has implementation

// Linker error: "undefined reference to initPCNT"

// ✅ With conditional declarations:
#if USE_HARDWARE_PCNT
  void initPCNT();      // Only declared if implemented
#else
  IRAM_ATTR void isrA(); // Only declared if implemented
#endif
// No linker errors!
```

### IRAM_ATTR Strategic Usage

```cpp
IRAM_ATTR void isrZ();
IRAM_ATTR void pcnt_overflow_handler(void* arg);
```

**IRAM_ATTR Deep Dive:**

```
Normal Function Storage:
┌─────────────────┐     ┌─────────────────┐
│ Flash Memory    │     │ CPU             │
│ (3.3V, slow)    │────▶│ (1.2V, fast)    │
│                 │     │                 │  
│ function_code() │     │ Execute         │
└─────────────────┘     └─────────────────┘
Access time: ~40-100 CPU cycles

IRAM Function Storage:
┌─────────────────┐     ┌─────────────────┐
│ Internal RAM    │     │ CPU             │  
│ (1.2V, fast)    │────▶│ (1.2V, fast)    │
│                 │     │                 │
│ iram_function() │     │ Execute         │
└─────────────────┘     └─────────────────┘
Access time: ~1-2 CPU cycles
```

**When to Use IRAM_ATTR:**
```cpp
// ✅ Critical ISRs (must be fast):
IRAM_ATTR void encoder_isr();

// ✅ Functions called from ISRs:
IRAM_ATTR void updateFromAB_Fast();

// ✅ High-frequency functions:
IRAM_ATTR uint32_t micros_fast();

// ❌ Regular functions (waste RAM):
IRAM_ATTR void printResults();  // No need!

// ❌ One-time functions:  
IRAM_ATTR void initEncoder();   // No need!
```

**IRAM Memory Cost:**
```
Available IRAM: ~400KB total
System usage: ~200KB
Available for user: ~200KB

IRAM_ATTR cost per function: ~100-500 bytes each
Must use carefully!
```

---

## 6. Hardware Abstraction Layer

### Dual-Mode Architecture

```cpp
// Platform-specific declarations:
#if USE_HARDWARE_PCNT
extern pcnt_unit_t pcnt_unit;
extern int16_t pcnt_overflow_count;
#endif

// Platform-independent interface:
void initEncoder();        // Works with both PCNT and ISR
int64_t getPosition();     // Unified interface
```

**Hardware Abstraction Benefits:**

```
┌─────────────────────────────────────────┐
│         Application Layer               │
│    ┌─────────────────────────────┐      │
│    │ main.cpp, display.cpp, etc. │      │
│    └─────────────────────────────┘      │
│                  ↕                      │
├─────────────────────────────────────────┤
│      Hardware Abstraction Layer        │  ← encoder.h interface
│    ┌─────────────┬─────────────────┐    │
│    │ getPosition │ getRPM          │    │
│    │ initEncoder │ updateSpeed     │    │
│    └─────────────┴─────────────────┘    │
│                  ↕                      │
├─────────────────────────────────────────┤
│         Hardware Layer                  │
│  ┌──────────┐              ┌──────────┐ │  
│  │   PCNT   │      OR      │   ISR    │ │
│  │ Hardware │              │ Software │ │
│  └──────────┘              └──────────┘ │
└─────────────────────────────────────────┘
```

**Code Reuse Benefits:**
```cpp
// Application code doesn't change:
void main() {
  initEncoder();           // Same call for both modes
  
  while(1) {
    float rpm = getRPM();  // Same call for both modes
    Serial.println(rpm);
    delay(100);
  }
}

// Only the implementation (encoder.cpp) changes internally
```

### Type Definitions & Forward Declarations

```cpp
extern pcnt_unit_t pcnt_unit;        // ESP-IDF type
extern int16_t pcnt_overflow_count;  // Standard type
```

**Forward Declaration Strategy:**
```cpp
// In header file:
extern pcnt_unit_t pcnt_unit;  // Declare existence

// In implementation file:
pcnt_unit_t pcnt_unit = PCNT_UNIT_0;  // Define actual variable
```

**Why not include everything?**
```cpp
// ❌ Heavy includes in header:
#include "driver/pcnt.h"        // 50KB of PCNT definitions
#include "soc/gpio_struct.h"    // 30KB of GPIO register maps
// Every file that includes encoder.h gets all this!

// ✅ Minimal includes in header:
extern pcnt_unit_t pcnt_unit;   // Just declare type usage
// Actual includes only in encoder.cpp where needed
```

---

## 7. Memory Layout & Performance

### Volatile Variable Placement

```cpp
extern volatile int64_t positionCounts;   // 8 bytes
extern volatile int8_t  lastStateAB;      // 1 byte  
extern volatile uint32_t lastEdgeMicros;  // 4 bytes
extern volatile uint32_t edgeDeltaMicros; // 4 bytes
extern volatile bool indexFlag;          // 1 byte
extern volatile int8_t lastDeltaSign;    // 1 byte
// Total volatile data: ~19 bytes
```

**Memory Access Performance:**

```
Volatile Variable Access Cost:
┌─────────────────────────────┬─────────────────┐
│ Variable Type               │ Access Cost     │
├─────────────────────────────┼─────────────────┤
│ int8_t (1 byte)            │ 1-2 CPU cycles  │
│ uint32_t (4 bytes, aligned)│ 1-2 CPU cycles  │  
│ int64_t (8 bytes)          │ 2-4 CPU cycles  │
│ bool (1 byte)              │ 1-2 CPU cycles  │
└─────────────────────────────┴─────────────────┘

Non-volatile access: ~1 CPU cycle (cached)
```

**Memory Alignment Considerations:**
```cpp
// ❌ Poor alignment (causes slowdowns):
struct EncoderState {
  volatile int8_t lastStateAB;      // Offset 0 (1 byte)
  volatile int64_t positionCounts;  // Offset 1 (misaligned!)
  volatile uint32_t lastEdge;       // Offset 9 (misaligned!)
};

// ✅ Good alignment (optimal access):  
struct EncoderState {
  volatile int64_t positionCounts;  // Offset 0 (8-byte aligned)
  volatile uint32_t lastEdge;       // Offset 8 (4-byte aligned)
  volatile int8_t lastStateAB;      // Offset 12 (any alignment OK)
};
```

### Function Pointer vs Direct Call Performance

```cpp
// Direct function calls (our approach):
void initEncoder();  // Direct call - compile-time binding

// vs Function pointer approach:
typedef void (*InitFunction)(void);
extern InitFunction initEncoder;  // Runtime binding

// Performance comparison:
// Direct call:     ~2-3 CPU cycles
// Function pointer: ~5-7 CPU cycles + potential cache miss
```

---

## 8. Advanced Header Techniques

### Inline Function Declarations

```cpp
inline uint32_t micros_fast();
```

**Inline vs Macro vs Function:**

```cpp
// 1. Macro (preprocessor):
#define MICROS_FAST() esp_timer_get_time()
// ✅ Zero overhead
// ❌ No type checking, debug issues

// 2. Regular function:
uint32_t micros_fast() { return esp_timer_get_time(); }
// ✅ Type safe, debuggable
// ❌ Function call overhead (~10 cycles)

// 3. Inline function (our choice):
inline uint32_t micros_fast() { return esp_timer_get_time(); }
// ✅ Zero overhead (when inlined)
// ✅ Type safe and debuggable
// ❌ Might not inline if too complex
```

**Inline Best Practices:**
```cpp
// ✅ Good inline candidates:
inline uint32_t micros_fast();           // Simple wrapper
inline bool isMoving(float speed);       // Simple logic

// ❌ Poor inline candidates:
inline void updateEncoderSpeed();        // Complex algorithm  
inline void initEncoder();              // Called once only
```

### Extern vs Static Linkage

```cpp
// External linkage (visible to other modules):
extern volatile int64_t positionCounts;  // Used by multiple .cpp files

// Internal linkage (private to module):
static volatile bool isInitialized;     // Only used within encoder.cpp
```

**Linkage Decision Matrix:**
```
┌─────────────────────┬─────────┬─────────────────────────┐
│ Usage Pattern       │ Keyword │ Visibility              │
├─────────────────────┼─────────┼─────────────────────────┤
│ Multiple modules    │ extern  │ Global (declare in .h)  │
│ Single module       │ static  │ File-local (define in .cpp)│
│ Constants           │ const   │ As appropriate          │
│ Macros              │ #define │ Global (if in .h)       │
└─────────────────────┴─────────┴─────────────────────────┘
```

### Template Specialization (Advanced)

```cpp
// Advanced: Generic encoder interface
template<typename PositionType>
class GenericEncoder {
  virtual void init() = 0;
  virtual PositionType getPosition() = 0;
  virtual float getRPM() = 0;
};

// Specialization for 64-bit position:
template<>
class GenericEncoder<int64_t> {
  // Our encoder implementation
};
```

### Namespace Management

```cpp
// Advanced: Namespace organization
namespace Encoder {
  namespace Hardware {
    void initPCNT();
    void initISR();
  }
  
  namespace Algorithm {
    float calculateEMA(float newVal, float oldVal, float alpha);
    float blendSpeeds(float window, float edge, float ratio);
  }
  
  // Public interface
  void init();
  float getRPM();
  int64_t getPosition();
}
```

---

## Συμπέρασμα: Header File as System Architecture

Το `encoder.h` αρχείο είναι **πολύ περισσότερο** από declarations - είναι το **αρχιτεκτονικό σχέδιο** του encoder subsystem:

### 🏗️ **Architectural Foundation**
- **Interface segregation** - καθαρές αφαιρέσεις
- **Dependency inversion** - hardware abstraction  
- **Single responsibility** - encoder-focused interface

### ⚡ **Performance Engineering**
- **Memory layout optimization** - aligned volatile variables
- **Conditional compilation** - zero-cost abstractions
- **IRAM placement** - critical path optimization

### 🔧 **Embedded Best Practices**
- **Volatile correctness** - threading safety
- **Atomic operations** - race condition prevention
- **Resource management** - minimal RAM/flash usage

### 📦 **Modular Design**
- **Clean interfaces** - easy testing and replacement
- **Hardware abstraction** - portable code
- **Feature flags** - configurable functionality

**Το encoder.h είναι ένα παράδειγμα σωστής embedded systems architecture - όπου κάθε byte μετράει, κάθε cycle είναι πολύτιμος, και η αξιοπιστία είναι υποχρεωτική.** 🎯

Η μελέτη αυτού του header file αποκαλύπτει τις βαθιές αρχές του **professional embedded development** - από memory management μέχρι hardware abstraction και performance optimization! 🚀
