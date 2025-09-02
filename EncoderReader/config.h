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

#endif // CONFIG_H
