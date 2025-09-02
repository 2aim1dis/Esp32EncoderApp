# Πλήρης Αναλυτική Τεχνική Ανάλυση Quadrature Encoder + Load Cell Firmware (GR / EN)

---
## 1. Περίληψη (GR)
Το firmware υλοποιεί υψηλής απόδοσης ανάγνωση incremental (quadrature) encoder (κανάλια A/B/Z) και σύστημα μέτρησης δύναμης με HX711 load cell σε ESP32-S3. Στόχος: ακριβής θέση (64‑bit), σταθερή και ταχέως αποκριτική υπολογισμένη ταχύτητα (counts/sec, rpm), συγχρονισμένη καταγραφή δύναμης, χαμηλή χρήση CPU, και ανθεκτικότητα σε θόρυβο. Υποστηρίζει δύο λειτουργίες καταμέτρησης: Hardware PCNT peripheral (προεπιλογή για μέγιστη απόδοση) και Optimized ISR fallback.

## 1. Executive Summary (EN)
The firmware provides a high-performance quadrature (A/B/Z) encoder and HX711 load cell acquisition stack on ESP32-S3. Goals: precise 64‑bit position tracking, low-latency / stable velocity estimation (cps, rpm), synchronized force data, minimal CPU overhead, and noise robustness. Two counting modes: hardware PCNT (default, highest throughput) and an optimized ISR fallback.

---
## 2. Αρχιτεκτονική / Architecture Overview
| Layer | Περιγραφή (GR) | Description (EN) |
|-------|----------------|------------------|
| Hardware Abstraction | Ρυθμίσεις pins, PCNT ή ISR, HX711 interface | GPIO setup, PCNT or ISR decode, HX711 sampling |
| Encoder Core | Καταμέτρηση pulses + state machine | Pulse counting + quadrature state machine |
| Velocity Engine | Window & edge metrics + adaptive blend + EMA | Window & edge velocity + adaptive blending + EMA smoothing |
| Load Cell Module | Μη μπλοκάρον ανάγνωση HX711, IIR φιλτράρισμα | Non-blocking HX711 acquisition + IIR filter |
| Command Parser | Σειριακές εντολές (TARE, CAL, RAW, SCALE, ZERO) | Serial commands parsing |
| Presentation | Μορφοποίηση εξόδου & startup status | Output formatting & startup banners |
| Integration Loop | Οργάνωση ενημερώσεων & περιοδικής εκτύπωσης | Orchestrates periodic updates & reporting |

---
## 3. Module Breakdown
### 3.1 `config.h`
GR: Κεντρικές παράμετροι (pins, PPR, ρυθμοί, φίλτρα, enable flags). EN: Central tuning & feature flags (pins, PPR, timing, filters, mode selection).

### 3.2 `encoder.h / encoder.cpp`
GR: Υλοποίηση δύο modes: PCNT (καταμέτρηση στο hardware με overflow επέκταση) ή optimized ISR (direct register reads + transition table). EN: Dual-mode implementation; PCNT hardware counting or fast ISR using GPIO register & lookup table. Περιλαμβάνει adaptive velocity, signed edge rate, EMA, timeout zeroing, Z index detection.

### 3.3 `loadcell.*`
GR: Μη μπλοκάρον loop-driven sampling: όταν το DOUT χαμηλό → διαβάζει 24-bit δείγμα, συσσωρεύει, average, offset (tare), scale calibration (counts/kg), IIR φίλτρο. EN: Non-blocking sampling triggered when DOUT low; accumulates N samples, averages, applies tare & scale, runs IIR (alpha=FORCE_IIR_ALPHA).

### 3.4 `commands.*`
GR: Parsing γραμμών serial (String έως newline). EN: Simple linear command dispatch; minimal latency; avoids parsing overhead loops.

### 3.5 `display.*`
GR: Ενοποιημένη μορφοποίηση εξόδου, διπλή γραμμή (Pos line + Force line). EN: Output composes single fused packet plus optional force-only line for external GUI parsers.

### 3.6 `EncoderReader.ino`
GR: Κύκλος: ενημέρωση αισθητήρων → υπολογισμός ταχύτητας → commands → περιοδική εκτύπωση. EN: Main application loop orchestrates modules with microsecond timing reference.

---
## 4. Δεδομένα & Κατάσταση / State Variables
| Variable | GR Περιγραφή | EN Description |
|----------|--------------|----------------|
| positionCounts (volatile 64b) | Συνολική θέση (ISR mode) | Cumulative position (ISR) |
| pcnt_overflow_count | Επέκταση 16-bit hardware counter | Extends PCNT 16-bit range |
| lastStateAB | Τελευταία δί-bit κατάσταση A/B | Previous A/B state |
| lastEdgeMicros | Χρόνος τελευταίας έγκυρης ακμής | Timestamp of last valid edge |
| edgeDeltaMicros | Διάστημα μικροδευτ. μεταξύ δύο ακμών | Interval between last two edges |
| lastDeltaSign | Πρόσημο τελευταίου βήματος | Sign of last delta |
| indexFlag | Σήμανση αν ελήφθη παλμός Z | Flag when index (Z) seen |
| emaCountsPerSec | Φιλτραρισμένη ταχύτητα cps | EMA smoothed velocity |
| lastSamplePos | Θέση προηγούμενου window δείγματος | Position at previous window sample |
| HX vars | Offset, scale, filteredForceKg | Load cell calibration & filtering |

---
## 5. Quadrature Decoding Logic
GR: Πίνακας `quadTable[16]` αποκωδικοποιεί έγκυρες μεταβάσεις (old<<2|new). Μη έγκυρα combos → 0 (απόρριψη θορύβου). EN: 4-bit index (old_state<<2 | new_state) into lookup that yields -1 / 0 / +1 delta.

ISR Mode Flow (pseudo):
```
read GPIO.in → extract A,B → compose newState
idx = ((lastStateAB & 0x3)<<2)|newState
delta = quadTable[idx]
if delta && (now-lastEdgeMicros >= MIN_EDGE_INTERVAL_US):
    positionCounts += delta
    edgeDeltaMicros = now-lastEdgeMicros
    lastEdgeMicros = now
    lastDeltaSign = sign(delta)
lastStateAB = newState
```

PCNT Mode: Hardware counts edges; B line supplies direction via control mode; code periodically reads extended 64-bit synthesized value `(overflows*65536 + current16) * 4` (logical multiplication factor).

---
## 6. Velocity Estimation Pipeline
GR:
1. Window Δcounts/Δt (σταθερό σε χαμηλές).
2. Edge-based 1e6/edgeΔt * sign (γρήγορη απόκριση).
3. Adaptive blend: low-speed → window, high-speed → edge-biased, mid-speed → mix.
4. Timeout → μηδενισμός αν δεν έρθουν edges.
5. EMA φίλτρο για εξομάλυνση.

EN:
1. Window velocity (Δcounts over sampling window).
2. Edge instantaneous (reciprocal of last edge interval, signed).
3. Adaptive blending heuristics.
4. Velocity timeout forces zero on inactivity.
5. EMA smoothing (α = EMA_ALPHA).

Outputs: `emaCountsPerSec`, plus derived `rpm = cps / PPR * 60`.

---
## 7. Load Cell Acquisition (HX711)
GR: Non-blocking: ελέγχει DOUT LOW → διαβάζει 24-bit frame (με interrupts κλειστά ελάχιστα), αποθηκεύει σε accumulator. Μετά από N δείγματα ή timeout → average, offset (tare), scale → άμεσο βάρος -> IIR φίλτρο.

EN: Polls readiness; reads sample with controlled SCK toggling; sign-extends 24-bit; averages batch; converts to kg using `(raw-offset)/scaleCountsPerKg`; applies IIR low-pass (FORCE_IIR_ALPHA).

---
## 8. Command Interface
| Command | GR | EN |
|---------|----|----|
| TARE | Μηδενισμός offset load cell | Zero load cell offset |
| CAL <kg> | Βαθμονόμηση scale | Calibrate scale factor |
| RAW | Ακατέργαστη μέτρηση | Raw HX711 reading |
| SCALE | Συντελεστής scale | Current counts/kg factor |
| ZERO | Μηδενισμός encoder | Reset encoder position |

Parsing: Single pass `if/else` chain for O(1) dispatch per command line.

---
## 9. Output Protocol
Primary line:
```
Pos=<counts> cps=<counts/sec> rpm=<rpm> force=<kg> [Z]
```
Secondary (force-only):
```
Force=<kg>
```
Rationale: Human readable + easily parsable with regex or token split.

---
## 10. Timing & Scheduling
| Mechanism | Purpose | Detail |
|-----------|---------|--------|
| `micros_fast()` | Unified microsecond timing | Uses ESP timer (esp_timer_get_time) |
| `SPEED_SAMPLE_US` | Window length | Governs output & velocity window sample |
| Edge ISR / PCNT | Position increments | High-resolution counting |
| HX accumulation | Oversampling | Improves SNR for force signal |
| Timeout logic | Velocity zeroing | `(now - lastEdgeMicros) > VELOCITY_TIMEOUT_US` |

---
## 11. Noise & Robustness Strategies
GR: Hardware filter (PCNT), ελάχιστο διάστημα ακμών, adaptive blending, EMA, ξεχωριστή index επεξεργασία. EN: Layered defense: hardware glitch reject, software temporal filter, adaptive estimator selection, EMA smoothing, timeout fallback.

---
## 12. Memory & Performance (Qualitative)
| Aspect | Comment |
|--------|---------|
| RAM Usage | Very low: few dozen bytes state |
| Flash Footprint | Small: single-purpose C++ modules |
| CPU Load PCNT | Near-zero for counting; only periodic math |
| CPU Load ISR | Proportional to edge rate; minimized by direct register logic |
| Latency | Velocity update every 10 ms (tunable) |

---
## 13. Scaling & Conversion
Formulas:
```
rev_per_sec = emaCountsPerSec / ENC_PPR
rpm = rev_per_sec * 60
angle_deg (optional) = (positionCounts * 360.0) / ENC_PPR
force_kg = (avgRaw - offset) / scaleCountsPerKg  (smoothed)
```

---
## 14. Extensibility Points
| Area | GR Ιδέα | EN Idea |
|------|--------|---------|
| Communication | Προσθήκη binary framing / CRC | Add framed binary protocol |
| Control | PID κλειστό βρόχο | Integrate closed-loop PID |
| Networking | WebSocket / MQTT | Publish over Wi-Fi / MQTT |
| Multi-Encoder | Πολλαπλές μονάδες PCNT | Multi-axis expansion |
| Calibration | Αυτόματη multi-point | Multi-point non-linear calibration |

---
## 15. Testing Strategy (Suggested)
GR:
1. Γεννήτρια παλμών για γνωστή συχνότητα → επαλήθευση cps.
2. Αλλαγές κατεύθυνσης → έλεγχος signed edge.
3. Τεχνητή παύση → timeout = 0 velocity.
4. Θόρυβος (π.χ. injection παλμών < κατωφλιού) → απόρριψη.
5. Load cell: τοποθέτηση γνωστού βάρους → CAL → επαναληπτικότητα.

EN:
1. Signal generator vs reported cps.
2. Direction reversals validate sign.
3. Idle period triggers zero.
4. Noise bursts below edge interval ignored.
5. Known weights validate scale stability.

---
## 16. Failure Modes & Mitigation
| Failure | Cause | Mitigation |
|---------|-------|------------|
| Missed counts (ISR mode) | Extremely high edge rate | Switch to PCNT / reduce PPR |
| Drifted force zero | Temperature drift | Re-issue TARE periodically |
| Velocity flicker low speed | Sparse edges | Window-pref + EMA tuned |
| Incorrect rpm | Wrong ENC_PPR | Adjust config.h |
| Spurious pulses | EMI / crosstalk | Shielding + MIN_EDGE_INTERVAL_US tuning |

---
## 17. Security / Safety Notes
GR: Δεν γίνεται validation εντολών πέρα από βασικό parsing—για βιομηχανική χρήση προτείνεται έλεγχος checksum ή fixed protocol. EN: For production add framing (STX/LEN/PAYLOAD/CRC) and reject malformed packets.

---
## 18. Design Rationale (Key Choices)
| Decision | Reason |
|----------|-------|
| PCNT default | Hardware reliability & zero ISR overhead |
| Adaptive blending | Balance responsiveness vs stability |
| EMA filter | O(1) time, minimal memory |
| Non-blocking HX711 | Prevents jitter in encoder timing |
| Text output | Human debug + simple parsing |

---
## 19. Pseudo Code (Full System) / Ψευδοκώδικας
```
setup():
  Serial.begin
  printSystemStatus()
  initEncoder()
  initLoadCell()

loop():
  now = micros_fast()
  updateLoadCell(now)
  updateEncoderSpeed(now)
  processSerialCommands()
  if now - lastOutput >= SPEED_SAMPLE_US:
     pos = getPosition()
     rpm = getRPM()
     cps = emaCountsPerSec
     force = getForceKg()
     indexSeen = indexFlag (atomic clear)
     printEncoderData(...)
     printForceData(force)
     lastOutput = now
```

---
## 20. Quick Reference (Cheat Sheet)
| Item | Value (Example) |
|------|-----------------|
| Sample window | 10 ms |
| Glitch filter | 10 µs |
| Velocity timeout | 500 ms |
| Force smoothing alpha | 0.15 |
| Velocity EMA alpha | 0.40 |

---
## 21. Glossary
| Term | GR | EN |
|------|----|----|
| PPR | Παλμοί ανά περιστροφή | Pulses per revolution |
| CPS | Μετρήσεις ανά δευτερόλεπτο | Counts per second |
| EMA | Εκθετικός Κινούμενος Μέσος | Exponential Moving Average |
| PCNT | Μετρητής παλμών hardware | Hardware pulse counter |
| IIR | Άπειρης κρουστικής απόκρισης φίλτρο | Infinite impulse response filter |

---
## 22. Συμπέρασμα / Conclusion
GR: Η λύση παρέχει ισχυρό, επεκτάσιμο και προσαρμόσιμο πλαίσιο ανάγνωσης encoder & load cell με ελάχιστη επιβάρυνση CPU και υψηλή ακρίβεια. EN: The system delivers a robust, extensible, and tunable backbone for high-integrity motion + force acquisition with industrial-grade reliability.

---
## 23. License / Usage Note
GR: Προσθέστε ενότητα άδειας εάν χρειάζεται (MIT, Apache κλπ). EN: Add a license file for distribution clarity.

---
Τέλος εγγράφου / End of document.
