# Τεχνική Τεκμηρίωση High-Performance Quadrature Encoder (ESP32-S3)

## 1. Σκοπός Συστήματος
Υλοποίηση αξιόπιστης και υψηλής ταχύτητας ανάγνωσης incremental (quadrature) encoder (A/B/Z) με ελάχιστο latency, χωρίς απώλεια παλμών, παροχή στιγμιαίας και φιλτραρισμένης ταχύτητας (cps, rpm) και ενσωμάτωση μετρήσεων δύναμης (load cell) σε ενιαία ροή δεδομένων μέσω σειριακής θύρας.

## 2. Κύρια Χαρακτηριστικά
| Δυνατότητα | Περιγραφή |
|-----------|-----------|
| Δύο modes | Hardware PCNT (προεπιλογή) ή Optimized ISR |
| Adaptive Velocity | Προσαρμοστική μίξη window-based & edge-based ταχύτητας |
| Signed Edge Speed | Διατήρηση κατεύθυνσης σε edge-based μέτρηση |
| Glitch Filtering | Χρονικό κατώφλι + hardware filter (PCNT) |
| Velocity Timeout | Άμεσο μηδενισμό ταχύτητας όταν σταματήσει ο encoder |
| Z / Index Support | Σήμανση αναφοράς (reference mark) |
| ZERO Command | Απευθείας μηδενισμός θέσης |
| Force Integration | Συνδυασμός θέσης / ταχύτητας / δύναμης σε ενιαίο output |
| Χαμηλό CPU Load | Hardware counting ή ελαχιστοποιημένη ISR λογική |

## 3. Δομή Αρχείων
| Αρχείο | Ρόλος |
|--------|------|
| `config.h` | Παράμετροι απόδοσης & συμπεριφοράς |
| `encoder.h / encoder.cpp` | Πυρήνας αποκωδικοποίησης encoder + velocity engine |
| `loadcell.*` | Ανάγνωση & φιλτράρισμα HX711 (δύναμη / βάρος) |
| `commands.*` | Σειριακές εντολές (TARE, CAL, RAW, SCALE, ZERO) |
| `display.*` | Μορφοποίηση / εκτύπωση δεδομένων & status |
| `EncoderReader.ino` | Κεντρικό `setup()` & `loop()` orchestrator |
| `README_HighPerformance.md` | Συνοπτική high-level βελτιστοποιημένη περιγραφή |
| `ENCODER_TECHNICAL_DOC.md` | (Τρέχον) Αναλυτική τεχνική τεκμηρίωση |

## 4. Ροή Εκκίνησης (Startup Flow)
1. `setup()`
   - `Serial.begin()`
   - `printSystemStatus()` (εμφανίζει ρυθμίσεις / mode)
   - `initEncoder()` (επιλέγει PCNT ή ISR)
   - `initLoadCell()` (προθέρμανση / calibration data)
2. `loop()` (εκτελείται συνεχώς)
   - Συλλογή force (`updateLoadCell()`)
   - Ενημέρωση ταχύτητας encoder (`updateEncoderSpeed()`)
   - Επεξεργασία εντολών (`processSerialCommands()`)
   - Περιοδική έξοδος πακέτου δεδομένων κάθε `SPEED_SAMPLE_US` μικροδευτ.

## 5. Modes: Hardware PCNT vs Optimized ISR
### 5.1 Hardware PCNT Mode (`USE_HARDWARE_PCNT=1`)
Χρησιμοποιεί το Pulse Counter peripheral:
- Increment σε επιλεγμένες ακμές (π.χ. θετικές του A) με κατεύθυνση μέσω του B (control)
- Εσωτερικό φίλτρο παλμών (glitch reject)
- 16-bit counter με overflow/underflow events -> επέκταση σε 64-bit μέσω `pcnt_overflow_count`
Πλεονεκτήματα: ελάχιστη χρήση CPU, μηδενικά χαμένα pulses σε πολύ υψηλές συχνότητες.

### 5.2 Optimized ISR Mode (`USE_HARDWARE_PCNT=0`)
Όταν δεν χρησιμοποιείται PCNT:
- Δύο interrupts (CHANGE) στα A/B
- Άμεση ανάγνωση καταχωρητή `GPIO.in` (bitmask) αντί `digitalRead()`
- Πίνακας μετάβασης `quadTable[16]` για ταχύ προσδιορισμό delta (-1,0,+1)
- Φίλτρο χρόνου: αγνόηση ακμών < `MIN_EDGE_INTERVAL_US`
Εστίαση στη μείωση latency & branch predictability.

## 6. Δομή Μεταβλητών (Encoder State)
| Μεταβλητή | Τύπος | Ρόλος |
|-----------|------|-------|
| `positionCounts` | int64_t (volatile) | Τρέχουσα σωρευτική θέση (counts) |
| `lastStateAB` | int8_t | Τελευταία αποκωδικοποιημένη δι-bit κατάσταση A/B |
| `lastEdgeMicros` | uint32_t | Χρόνος τελευταίας έγκυρης ακμής |
| `edgeDeltaMicros` | uint32_t | Διάστημα μικροδευτ. μεταξύ δύο έγκυρων ακμών |
| `lastDeltaSign` | int8_t | Πρόσημο τελευταίας αλλαγής (κατεύθυνση) |
| `indexFlag` | bool | Ένδειξη ότι ελήφθη Z (index) παλμός |
| `emaCountsPerSec` | float | Φιλτραρισμένη (EMA) ταχύτητα σε counts/sec |
| `lastSamplePos` | int64_t | Θέση στην προηγούμενη δειγματοληψία window |
| `pcnt_overflow_count` | int16_t | Επέκταση PCNT overflows (μόνο PCNT mode) |

## 7. Quadrature Decoding
Η μετάβαση κωδικοποιείται ως (old_state << 2) | new_state. Ο πίνακας `quadTable[16]` χαρτογραφεί σε delta. Μη έγκυρες / ταυτόχρονες μεταβολές (πιθανό θόρυβο) επιστρέφουν `0` ώστε να αγνοηθούν.

## 8. Velocity Pipeline

### Recent Fix (September 2025): PCNT Speed Calculation
**Issue Resolved:** Hardware PCNT mode now properly calculates velocity (cps/RPM).

**Previous Problem:** PCNT mode bypassed ISR timing variables, causing speed to always show 0.0.

**Solution Implemented:** Mode-specific velocity calculation:

#### PCNT Mode Velocity Calculation:
1. **Raw Counts (positionCounts)** from hardware PCNT peripheral
2. **Window-Based Speed Only**: (Δcounts / Δt) per `SPEED_SAMPLE_US` period
3. **No Edge-Based Calculation**: Hardware doesn't provide inter-edge timing
4. **No Velocity Timeout**: Not applicable for continuous hardware counting
5. **EMA Filter**: Same filtering as ISR mode

#### ISR Mode Velocity Calculation (Unchanged):
1. **Raw Counts (positionCounts)** updated per ISR edge
2. **Window-Based Speed**: (Δcounts / Δt) per period
3. **Edge-Based Speed**: 1e6 / `edgeDeltaMicros` * `lastDeltaSign`  
4. **Adaptive Blend**: Intelligent mixing based on speed magnitude
5. **Velocity Timeout**: Force zero when no edges for `VELOCITY_TIMEOUT_US`
6. **EMA Filter**: Smoothing with configurable alpha

### Unified Velocity Pipeline:
1. **Raw Counts (positionCounts)** ενημερώνονται ανά edge.
2. **Window-Based Speed (cpsWindow)**: (Δcounts / Δt) ανά περίοδο `SPEED_SAMPLE_US`.
3. **Edge-Based Speed (cpsEdge)**: 1e6 / `edgeDeltaMicros` * `lastDeltaSign`.
4. **Adaptive Blend**:
   - Αν |cpsWindow| < 10 → χρήση window (σταθερότητα σε πολύ χαμηλές στροφές)
   - Αν |cpsWindow| > 1000 && edge διαθέσιμη → 70% edge + 30% window
   - Αλλιώς → 50/50 (ή fallback σε όποια διαθέσιμη)
5. **Timeout**: Αν `currentTime - lastEdgeMicros > VELOCITY_TIMEOUT_US` → velocity=0
6. **EMA**: `emaCountsPerSec = α * blended + (1-α) * emaCountsPerSec`

## 9. Φίλτρα & Σταθεροποίηση
| Στρώση | Περιγραφή |
|--------|-----------|
| Hardware Filter (PCNT) | Απορρίπτει short pulses < ~1µs |
| Software Edge Interval | Αγνοεί edges < `MIN_EDGE_INTERVAL_US` |
| Adaptive Blend | Επιλέγει πιο αξιόπιστη πηγή ταχύτητας δυναμικά |
| EMA | Εξομαλύνει διακυμάνσεις υψηλής συχνότητας |
| Timeout | Άμεσο μηδενισμό σε παύση κίνησης |

## 10. Index (Z) Handling
- ISR στο `ENC_PIN_Z` (RISING) θέτει `indexFlag = true`.
- Δυνατότητα (σχολιασμένη) για αυτόματο μηδενισμό θέσης πάνω στον Z.
- Χρήση: alignment, homing, revolution tagging.

## 11. Εντολές (Serial Commands)
| Εντολή | Λειτουργία |
|--------|------------|
| `TARE` | Μηδενισμός (offset) load cell |
| `CAL <kg>` | Βαθμονόμηση scale με γνωστό βάρος |
| `RAW` | Εκτύπωση ακατέργαστης τιμής HX711 |
| `SCALE` | Εμφάνιση συντελεστή scaling load cell |
| `ZERO` | Reset encoder position |

## 12. Μορφή Εξόδου
Πρωτεύουσα γραμμή:
```
Pos=<counts> cps=<counts/sec> rpm=<rpm> force=<kg> [Z]
```
Δευτερεύουσα (συμβατότητα GUI):
```
Force=<kg>
```
Χρησιμοποιείται απλή μορφοποίηση ώστε ο Python client να κάνει parsing εύκολα.

## 13. Μετατροπές & Scaling
| Μέγεθος | Υπολογισμός |
|---------|-------------|
| Revolutions/sec | `emaCountsPerSec / ENC_PPR` |
| RPM | `getRPM()` → rev/s * 60 |
| Force (kg) | Από φίλτρο load cell (`FORCE_IIR_ALPHA`) |
| Θέση σε rev | `positionCounts / (float)ENC_PPR` |
| Γωνία (deg) | `(positionCounts * 360.0f) / ENC_PPR` (αν απαιτηθεί επέκταση) |

## 14. Διαχείριση Χρόνου
| Συνάρτηση | Χρήση |
|-----------|-------|
| `micros_fast()` | Ενιαία πρόσβαση στο 64-bit microsecond timer (ESP timer) |
| `SPEED_SAMPLE_US` | Περιοδικό παράθυρο ενημέρωσης ταχύτητας / εκτύπωσης |
| `edgeDeltaMicros` | Διάστημα μεταξύ δύο τελευταίων έγκυρων ακμών |
| `VELOCITY_TIMEOUT_US` | Όριο παύσης κίνησης |

## 15. Απόδοση & Χρονικές Εκτιμήσεις (Updated September 2025)
| Σενάριο | PCNT Mode | ISR Mode (Optimized) |
|---------|-----------|----------------------|
| Pulse Throughput | >100 kHz | ~50 kHz+ (ανάλογα CPU load) |
| CPU Overhead | Πολύ χαμηλό (~2%) | Χαμηλό (~15% @ 50kHz) |
| Velocity Accuracy | ✅ Window-based (Fixed) | ✅ Adaptive blend |
| Latency Ταχύτητας | ~10 ms | ~10 ms |
| Position Accuracy | ✅ Hardware perfect | ✅ Software excellent |
| Speed Calculation | ✅ Fixed (Sept 2025) | ✅ Full featured |

## 16. Κύριες Παράμετροι (`config.h`)
| Macro | Ρόλος | Επίδραση |
|-------|------|----------|
| `ENC_PPR` | Pulses per revolution | Επηρεάζει scaling rpm/rev |
| `SPEED_SAMPLE_US` | Παράθυρο υπολογισμού | Trade-off latency / ομαλότητας |
| `EMA_ALPHA` | Βάρος EMA | Υψηλότερο = πιο responsive |
| `USE_HARDWARE_PCNT` | Επιλογή mode | PCNT ή ISR |
| `MIN_EDGE_INTERVAL_US` | Glitch reject | Noise filtering vs max speed |
| `VELOCITY_TIMEOUT_US` | Zero timeout | Stop detection latency |
| `ADAPTIVE_BLENDING` | Προσαρμοστική μίξη | Βελτίωση σταθερότητας |
| Force related | HX711 pins & φίλτρο | Επεξεργασία δύναμης |

## 17. Ρύθμιση / Συντονισμός (Tuning Guidelines)
| Στόχος | Παράμετρος | Κατεύθυνση |
|--------|------------|------------|
| Πιο γρήγορη απόκριση | `SPEED_SAMPLE_US` | Μείωση (π.χ. 5000) |
| Λιγότερος θόρυβος | `EMA_ALPHA` | Μείωση (π.χ. 0.25) |
| Λιγότερα ψευδο-pulses | `MIN_EDGE_INTERVAL_US` | Αύξηση (π.χ. 15–20) |
| Ταχύτερος μηδενισμός | `VELOCITY_TIMEOUT_US` | Μείωση |
| Σταθερό low-speed velocity | Adaptive blend | Ενεργό (1) |

## 18. Troubleshooting (Updated September 2025)
| Σύμπτωμα | Πιθανή Αιτία | Διορθωτική Ενέργεια |
|----------|-------------|---------------------|
| Χάνονται παλμοί | Πολύ υψηλό rate σε ISR mode | Ενεργοποίησε PCNT / Μείωσε θόρυβο |
| Τρεμόπαιγμα ταχύτητας σε χαμηλές στροφές | Edge noise | Adaptive blending / αυξ. window |
| Καθυστερημένη μηδενική ταχύτητα | Timeout πολύ μεγάλο | Μείωσε `VELOCITY_TIMEOUT_US` |
| RPM λάθος | Λάθος `ENC_PPR` | Διόρθωσε ρύθμιση στο `config.h` |
| Position jumps | Noise/vibration | Αυξ. `MIN_EDGE_INTERVAL_US` |
| ~~Speed shows 0.0 in PCNT mode~~ | ~~PCNT timing issue~~ | ✅ **FIXED** (September 2025) |

## 19. Επεκτάσεις (Future Enhancements)
- Αυτόματη αναγνώριση encoder resolution (αν υποστηρίζεται από ανώτερο layer)
- PID loop integration / real-time control channel
- Προσθήκη CAN / Ethernet output
- Χρονική σφράγιση (timestamp) σε πακέτα για συγχρονισμό multi-sensor
- Προαιρετικός median filter layer

## 20. Checklist Υλοποίησης Υψηλής Απόδοσης (Updated September 2025)
☑ Hardware PCNT υποστήριξη  
☑ Direct register GPIO reads  
☑ Signed edge velocity  
☑ Adaptive blending  
☑ Velocity timeout  
☑ Glitch filtering  
☑ ZERO command  
☑ **PCNT speed calculation fix** ← **NEW (September 2025)**  
☑ Mode-specific velocity algorithms ← **NEW (September 2025)**  
☑ Τεκμηρίωση & tuning οδηγός  

## 21. FAQ
**Ε: Γιατί δεν μετράει και τις αρνητικές ακμές στο PCNT;**  
Α: Επιλογή για μείωση διπλασιασμού παλμών. Η κατεύθυνση δίνεται από B (control). Μπορείς να αλλάξεις `pos_mode/neg_mode` αν θέλεις full 4x.

**Ε: Μπορώ να έχω πιο γρήγορη έξοδο (<10ms);**  
Α: Ναι, μείωσε `SPEED_SAMPLE_US` (π.χ. 5000). Περισσότερο jitter σε velocity όμως.

**Ε: Θέλω πιο “γυαλισμένη” ταχύτητα.**  
Α: Μείωσε `EMA_ALPHA` και / ή αύξησε `SPEED_SAMPLE_US`.

**Ε: Θέλω πιο άμεση αντίδραση σε αλλαγές κατεύθυνσης.**  
Α: Αύξησε `EMA_ALPHA` (π.χ. 0.55) και βεβαιώσου ότι adaptive blending είναι ενεργό.

## 22. Συνοπτική Περιγραφή Ροής (Pseudo Flow)
```
setup():
  Serial.begin
  printSystemStatus
  initEncoder (PCNT ή ISR)
  initLoadCell

loop():
  now = micros_fast()
  updateLoadCell(now)
  updateEncoderSpeed(now)
  processSerialCommands()
  αν (now - lastOutput >= SPEED_SAMPLE_US):
     διαβάζω θέση, rpm, cps, force
     εκτυπώνω packet
```

---
Τεκμηρίωση συντάχθηκε για να λειτουργήσει ως πλήρης οδηγός κατανόησης, ρύθμισης και μελλοντικής επέκτασης του συστήματος. Για απορίες ή περαιτέρω αυτοματοποίηση (π.χ. integration με control loops) μπορεί να προστεθεί επιπλέον ενότητα API.
