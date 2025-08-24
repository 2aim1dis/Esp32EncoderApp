#ifndef CONFIG_H
#define CONFIG_H

// ====== ENCODER CONFIG ======
#define ENC_PIN_A    16
#define ENC_PIN_B    17
#define ENC_PIN_Z    18
#define ENC_PPR      1024      // Set to your encoder's pulses per revolution
#define USE_INDEX    1         // 1 = enable Z handling, 0 = disable
#define SPEED_SAMPLE_US 50000  // 50 ms reporting window
#define EMA_ALPHA    0.30f     // 0..1 (higher = more responsive, lower = smoother)

// ====== LOAD CELL / HX711 CONFIG (LP7145C 300kg) ======
// LoadCell 1
#define HX711_DOUT_PIN_1   40   // Data pin (DOUT) for LoadCell 1
#define HX711_SCK_PIN_1    41   // Clock pin (SCK) for LoadCell 1
// LoadCell 2
#define HX711_DOUT_PIN_2   42   // Data pin (DOUT) for LoadCell 2
#define HX711_SCK_PIN_2    43   // Clock pin (SCK) for LoadCell 2
// Common settings
#define HX711_READ_SAMPLES 8  // Oversampling per report window
#define FORCE_IIR_ALPHA  0.15f // Low-pass for force (0..1)
#define NUM_LOADCELLS    2     // Number of load cells

#endif // CONFIG_H
