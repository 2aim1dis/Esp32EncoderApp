#ifndef CONFIG_H
#define CONFIG_H

// ====== ENCODER CONFIG ======
#define ENC_PIN_A    16
#define ENC_PIN_B    17
#define ENC_PIN_Z    18
#define ENC_PPR      1024      // Set to your encoder's pulses per revolution
#define USE_INDEX    1         // 1 = enable Z handling, 0 = disable
#define SPEED_SAMPLE_US 10000  // 10 ms reporting window (5x faster)
#define EMA_ALPHA    0.40f     // 0..1 (higher = more responsive, lower = smoother)

// ====== HIGH PERFORMANCE CONFIG ======
#define USE_HARDWARE_PCNT  1   // 1 = use ESP32 PCNT peripheral, 0 = use ISR
#define MIN_EDGE_INTERVAL_US 10 // Minimum time between edges to filter glitches
#define VELOCITY_TIMEOUT_US  500000 // 500ms - zero velocity if no edges
#define ADAPTIVE_BLENDING 1    // 1 = adaptive window/edge blending, 0 = fixed 50/50

// ====== LOAD CELL / HX711 CONFIG (LP7145C 300kg) ======
#define HX711_DOUT_PIN   40   // Data pin (DOUT)
#define HX711_SCK_PIN    41   // Clock pin (SCK)
#define HX711_READ_SAMPLES 8  // Oversampling per report window
#define FORCE_IIR_ALPHA  0.15f // Low-pass for force (0..1)

#endif // CONFIG_H
