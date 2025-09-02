<!--
  File: ENCODER_PATH_EXAMPLE_GR.md
  Purpose: Step-by-step example showing the encoder signal -> ISR/PCNT -> velocity fusion -> serial -> Python GUI path
-->

# Παράδειγμα: Ποιο path ακολουθεί η πληροφορία από τον encoder μέχρι την GUI (βήμα‑βήμα)

Περιλαμβάνονται: timeline με γεγονότα, ο κώδικας σε κάθε βήμα (Arduino C++), και το path στην Python GUI.

## Σύντομο receipt & σχέδιο

- Στόχος: Να έχεις ένα αρχείο που δείχνει με αριθμούς και κώδικα πώς περνάει η πληροφορία.
- Σχέδιο: 1) Δώσαμε timeline σήματος, 2) δείχνουμε ISR / PCNT, 3) window + edge calc, 4) blending + EMA, 5) serial → Python parsing → GUI.

## Checklist (τι περιέχει αυτό το αρχείο)
- [x] Timeline σήματος (μικροδευτερόλεπτα και counts)
- [x] ISR implementation snippet και εξήγηση
- [x] PCNT fallback snippet
- [x] Window calculation snippet
- [x] Edge calculation snippet
- [x] Blending + EMA snippet
- [x] Serial reporting snippet
- [x] Python parsing snippet και GUI path
- [x] Πλήρες numeric παράδειγμα βήμα‑βήμα

---

## 1) Σύντομη ροή δεδομένων

- Hardware: encoder A/B → ESP32 GPIO (ή PCNT).
- Acquisition: ISR (timestamps + increment) ή PCNT (hardware counter).
- Aggregation: positionCounts (volatile) ή pcnt counter.
- Velocity compute: window method (cpsWindow) + edge method (cpsEdge).
- Fusion: adaptive blending → EMA smoothing → filteredVelocity.
- Output: Serial line "Pos=.. cps=.. rpm=.." → Python serial reader → DataBuffer → GUI table/plot.

---

## 2) Υποθετικά δεδομένα / waveform

- Encoder: PPR = 1024, 4x decoding → countsPerRev = 4096.
- Timestamp units: microseconds (μs).
- Παράθυρο ταχύτητας: SPEED_SAMPLE_US = 10000 μs (10 ms).

Events (παράδειγμα):
- t = 0 μs: initial positionCounts = 1000
- t = 2_000 μs: ISR edge → step = +1 → positionCounts = 1001, prevEdge = 2000
- t = 4_000 μs: ISR edge → step = +1 → positionCounts = 1002, lastEdgeDelta = 2000 μs
- t = 6_000 μs: ISR edge → step = +1 → positionCounts = 1003, lastEdgeDelta = 2000 μs
- t = 8_000 μs: ISR edge → step = +1 → positionCounts = 1004, lastEdgeDelta = 2000 μs
- t = 10_000 μs: window tick (every 10 ms) — compute window-based value

---

## 3) ISR path — τι κάνει το ISR όταν έρχεται ακμή

```cpp
// filepath: EncoderReader/encoder.cpp
// Very short ISR - update position and timestamps
IRAM_ATTR void IRAM_ATTR handle_encoder_edge() {
    uint8_t newState = readABfast(); // 0..3
    uint8_t trans = (lastStateAB << 2) | newState;
    int8_t delta = quadTable[trans]; // -1, 0, +1
    if (delta) {
        positionCounts += delta;              // volatile global
        lastDeltaSign = (delta > 0) ? 1 : -1;
        uint32_t now = micros();
        lastEdgeDelta = now - lastEdgeMicros; // μs
        lastEdgeMicros = now;
    }
    lastStateAB = newState;
}
```

Επεξήγηση:
- Κάθε ακμή A/B τρέχει πολύ σύντομη ISR που ενημερώνει positionCounts και timestamps (lastEdgeMicros, lastEdgeDelta).

---

## 4) PCNT path — τι γίνεται αν είσαι σε PCNT mode

```cpp
// filepath: EncoderReader/encoder.cpp
#if USE_HARDWARE_PCNT
void initPCNT() {
  // configure PCNT unit/channel
}
int64_t readPositionPCNT() {
  int16_t cnt;
  pcnt_get_counter_value(PCNT_UNIT_0, &cnt);
  return pcnt_accumulated + (int64_t)cnt;
}
#endif
```

Επεξήγηση:
- Το hardware PCNT μετρά counts χωρίς ISR. Δεν δίνει edge timestamps, άρα cpsEdge δεν υποστηρίζεται (εκτός αν προσθέσεις ISR μόνο για timestamps).

---

## 5) Window method — υπολογισμός `cpsWindow` (κάθε SPEED_SAMPLE_US)

```cpp
// filepath: EncoderReader/encoder.cpp
void updateEncoderSpeed() {
  uint32_t now = micros();
  if ((now - lastWindowTime) < SPEED_SAMPLE_US) return;
  noInterrupts();
  int64_t posNow = positionCounts; // ή readPositionPCNT()
  interrupts();
  int64_t deltaCounts = posNow - lastWindowPos;
  float windowSec = (now - lastWindowTime) / 1e6f;
  float cpsWindow = (windowSec > 0) ? (deltaCounts / windowSec) : 0.0f;
  lastWindowPos = posNow;
  lastWindowTime = now;
  // αποθήκευσε cpsWindow για blending
}
```

Επεξήγηση:
- `cpsWindow` = average counts/sec μέσα στο παράθυρο (π.χ. 10 ms).

---

## 6) Edge method — υπολογισμός `cpsEdge` (από `lastEdgeDelta`)

```cpp
// filepath: EncoderReader/encoder.cpp
float computeEdgeCps() {
  uint32_t delta_us = lastEdgeDelta; // volatile
  if (delta_us == 0) return 0.0f;
  float cpsEdge = 1e6f / (float)delta_us;
  cpsEdge *= (float)lastDeltaSign; // apply direction
  return cpsEdge;
}
```

Επεξήγηση:
- `cpsEdge` = στιγμιαία εκτίμηση από το τελευταίο edge interval (πολύ άμεσο, πιο θορυβώδες).

---

## 7) Blending + EMA — πώς φτιάχνεται η τελική τιμή

```cpp
// filepath: EncoderReader/encoder.cpp
void fuseAndFilter(float cpsWindow, float cpsEdge) {
  float absW = fabsf(cpsWindow), absE = fabsf(cpsEdge);
  float blended;
  if (absW < 10.0f) {
    blended = cpsWindow; // very low speed
  } else if (absW > 1000.0f && absE > 0.0f) {
    blended = 0.7f * cpsEdge + 0.3f * cpsWindow; // high speed
  } else {
    if (absE > 0.0f) blended = 0.5f * (cpsWindow + cpsEdge);
    else blended = cpsWindow;
  }
  const float alpha = 0.2f;
  emaCountsPerSec = alpha * blended + (1.0f - alpha) * emaCountsPerSec;
}
```

Επεξήγηση:
- `blended` είναι ο ωμός συνδυασμός. EMA (α) δίνει ομαλότερο αποτέλεσμα.

---

## 8) Serial output — τι στέλνει το ESP32

```cpp
// filepath: EncoderReader/EncoderReader.ino
void report() {
  int64_t pos = readPosition();
  float cps = emaCountsPerSec;
  float rpm = cps / (countsPerRev) * 60.0f;
  Serial.printf("Pos=%lld cps=%.2f rpm=%.2f\n", pos, cps, rpm);
}
```

Επεξήγηση:
- Αυτή η ASCII γραμμή διαβάζεται από την Python.

---

## 9) Python side — parsing & buffer

```python
# filepath: python_client/serial_handler.py
import re, time
LINE_RE = re.compile(r'Pos=(?P<pos>-?\d+)\s+cps=(?P<cps>[-\d.]+)\s+rpm=(?P<rpm>[-\d.]+)')
def on_serial_line(line: str):
    m = LINE_RE.search(line)
    if not m:
        return
    pos = int(m.group('pos'))
    cps = float(m.group('cps'))
    rpm = float(m.group('rpm'))
    ts = time.time()
    sample = Sample(timestamp=ts, pulses=pos, velocity_cps=cps, rpm=rpm)
    data_buffer.add(sample)

# Η GUI ανανεώνει κάθε UI_REFRESH_MS και παίρνει νέα δείγματα από το buffer
```

Επεξήγηση:
- Η Python κάνει regex, δημιουργεί `Sample` και το αποθηκεύει στο `DataBuffer`.

---

## 10) GUI path — τι γίνεται μετά το buffer

- `DataBuffer` κρατά λίστα samples, υπολογίζει delta (pos diff), παρέχει slices για plotting.
- Η κύρια GUI (Tkinter) ανανεώνει κάθε `UI_REFRESH_MS` και παίρνει τα νέα δείγματα από το buffer (μέσω lock).

---

## 11) Πλήρες numeric παράδειγμα (βήμα‑βήμα)

Given:
- countsPerRev = 4096
- initial pos = 1000
- lastWindowPos before tick = 1000
- lastEdgeDelta at tick = 2000 μs
- During 10 ms window (0→10ms) είχαμε 12 νέα steps → posNow = 1012

Computations at t = 10_000 μs:
- deltaCounts = 1012 - 1000 = 12
- windowSec = 0.01 s
- cpsWindow = 12 / 0.01 = 1200 cps
- cpsEdge = 1e6 / 2000 = 500 cps (direction +1)
- absW = 1200 → high speed branch → blended = 0.7*500 + 0.3*1200 = 710 cps
- EMA (α=0.2, prev=600) → ema = 0.2*710 + 0.8*600 = 622 cps
- rpm = 622 / 4096 * 60 ≈ 9.11 rpm
- Serial: `Pos=1012 cps=622.00 rpm=9.11`

Python receives line → parses pos=1012, cps=622 → appends to `DataBuffer` → table & plot update.

---

## 12) Hybrid: PCNT + ISR timestamps

- Μπορείς να διαβάζεις θέση από PCNT (χωρίς lost pulses) αλλά να έχεις μικρή ISR για timestamps (attachInterrupt on A). Με αυτό παίρνεις αξιόπιστο pos και edge timing.

---

## 13) Πρακτικά debugging tips
- Δεν αυξάνεται pos → έλεγξε wiring/pull‑ups/GND.
- pos αυξάνει αλλά cps=0 → ISR δεν ενημερώνει lastEdgeDelta.
- jitter σε cps → μείωσε alpha (EMA) ή αύξησε παράθυρο.
- χάνεις counts σε high speed ISR mode → switch σε PCNT.

---

## 14) Τι μπορώ να προσθέσω
- Demo sketch `demo_trace.ino` που τυπώνει όλα τα internal vars σε κάθε window tick.
- Python test script που παράγει σειριακές γραμμές για unit testing του parser/GUI.

---

*(Το αρχείο βασίζεται στον υπάρχοντα κώδικα του repo: `encoder.cpp`, `config.h`, `EncoderReader.ino`, `python_client/serial_handler.py`.)*
