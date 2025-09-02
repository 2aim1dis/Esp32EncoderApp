# Πλήρης Ανάλυση: Πώς Μετράει ο Encoder (ESP32-S3 Omron E6B2-CWZ6C)

## Στόχος
Να εξηγηθεί με ακρίβεια πώς υπολογίζεται Θέση και Ταχύτητα (Counts, CPS, RPM) στο firmware:  
- Μηχανισμός Quadrature (A,B,Z)  
- Δύο τρόποι μέτρησης: PCNT peripheral και ISR (interrupt edges)  
- Dual Method Velocity Engine: windowSec & cpsWindow + edge timing (cpsEdge) + adaptive blending  
- Ρόλος σταθερών (`SPEED_SAMPLE_US`, thresholds 10 / 1000 cps, EMA κλπ.)

---
## 1. Βασική Αρχή Quadrature
Ο Omron E6B2-CWZ6C δίνει δύο κανάλια: A και B, 90° φάση.  
Παρατηρώντας τη μετάβαση (edges) σε A και το επίπεδο του B (ή αντίστροφα) ξέρουμε κατεύθυνση.  
Κύκλος sequence: 00 → 01 → 11 → 10 → 00 (CW) ή το ανάστροφο (CCW).  
Για PPR=1024 (παλμοί ανά μηχανικό γύρο στο κανάλι), με 4x decoding παίρνεις 4096 counts ανά revolution.

Θέση (position) = Συσσωρευτικό άθροισμα (+1 ή -1) ανά έγκυρο βήμα sequence.

---
## 2. Δύο Υλοποιήσεις Μέτρησης Θέσης
### 2.1 ISR (Software Quadrature Decode)
- Ορίζονται interrupts σε RISING/FALLING (ή μόνο σε μία ακμή) στα pins A/B.  
- Το ISR διαβάζει A,B, ενημερώνει state machine και αυξομειώνει έναν signed counter.  
- Πλεονέκτημα: Πολύ μικρή καθυστέρηση, δυνατότητα edge timestamp για high‑resolution velocity.  
- Μειονέκτημα: CPU load σε πολύ υψηλές συχνότητες, πιθανότητα jitter αν πολλά άλλα interrupts.

### 2.2 PCNT Peripheral (Pulse Counter)
- ESP32-S3 hardware μετρητής παλμών: διαμορφώνεται input A (pulse) + B (control/direction).  
- Το hardware αυξομειώνει έναν εσωτερικό 16/32-bit counter (με όρια).  
- Firmware περιοδικά διαβάζει τον PCNT count και τον επαναφέρει (ή κρατά offset) ανά παράθυρο.  
- Πλεονέκτημα: Ελάχιστο CPU overhead, σταθερό σε υψηλές ταχύτητες.  
- Μειονέκτημα: Δεν έχει μεμονωμένα timestamps κάθε edge → δεν μπορείς να πάρεις ακριβές edge interval για adaptive blending (οπότε μένεις μόνο με window method).

---
## 3. Υπολογισμός Ταχύτητας – Διπλή Προσέγγιση (Dual Method)
Στόχος: Σταθερή ένδειξη σε χαμηλές ταχύτητες & γρήγορη απόκριση σε υψηλές.  
Χρησιμοποιούμε δύο μετρικές:

1. Window-Based Velocity (`cpsWindow`): Δcounts / Δt μέσα σε χρονικό παράθυρο (windowSec).  
2. Edge-Based Velocity (`cpsEdge`): 1 / (edgeIntervalSec) * sign, βασισμένο στο τελευταίο χρόνο μεταξύ διαδοχικών valid edges.

Adaptive blending επιλέγει ή συνδυάζει:  
- Low speed (<10 cps): μόνο window (λιγότερο jitter).  
- High speed (>1000 cps): 70% edge + 30% window (edge δίνει latency ~μηδέν).  
- Μέση ζώνη: 50/50 ή fallback αν λείπει κάποιο.

Με PCNT mode δεν έχουμε edge timestamps → χρησιμοποιείται μόνο `cpsWindow` (blended=window).

---
## 4. Σταθερές & Ορισμοί
| Σύμβολο | Περιγραφή | Παράδειγμα |
|---------|-----------|------------|
| `SPEED_SAMPLE_US` | Διάρκεια sampling window σε microseconds | 10000 (10ms) |
| `windowSec` | (currentTime - lastSample)/1e6 | ~0.010 s |
| `deltaCounts` | posNow - lastSamplePos | π.χ. 40 counts |
| `cpsWindow` | deltaCounts / windowSec | 40 / 0.010 = 4000 cps |
| `edgeIntervalSec` | Χρόνος μεταξύ δύο edges (ISR mode) | π.χ. 250µs = 0.00025 s |
| `cpsEdge` | 1 / edgeIntervalSec | 4000 cps |
| Thresholds | 10 / 1000 cps | Προσαγωγή blending |
| EMA | Εκθετική εξομάλυνση τελικού cps | π.χ. α=0.2 |

---
## 5. Ροή Υπολογισμού (ISR Mode)
```
loop():
  now = micros()
  if (now - lastSample >= SPEED_SAMPLE_US):
     posNow = positionCounter
     deltaCounts = posNow - lastSamplePos
     windowSec = (now - lastSample)/1e6
     cpsWindow = deltaCounts / windowSec
     // edge data ήδη ενημερώνεται μέσα στο ISR:
     //   lastEdgeIntervalSec = (lastEdgeMicros - prevEdgeMicros)/1e6
     cpsEdge = (lastEdgeIntervalSec > 0) ? 1 / lastEdgeIntervalSec : 0
     absWindow = abs(cpsWindow)
     absEdge   = abs(cpsEdge)
     if (absWindow < 10): blended = cpsWindow
     else if (absWindow > 1000 && absEdge > 0): blended = 0.7*cpsEdge + 0.3*cpsWindow
     else: blended = combine 50/50 (όπου υπάρχει)
     // EMA
     filtered = emaAlpha * blended + (1-emaAlpha)*prevFiltered
     lastSamplePos = posNow
     lastSample = now
     publish(posNow, filtered)
```

ISR (edge):
```
ISR on edge:
  now = micros()
  read A,B -> decode direction -> positionCounter += (+/-1)
  edgeInterval = now - prevEdgeTime
  prevEdgeTime = now
  store edgeInterval for cpsEdge
```

---
## 6. Ροή Υπολογισμού (PCNT Mode)
```
loop():
  now = micros()
  if (now - lastSample >= SPEED_SAMPLE_US):
     countNow = pcnt_get_and_clear()   // ή read & subtract baseline
     deltaCounts = countNow            // αν μηδενίζουμε κάθε παράθυρο
     windowSec = (now - lastSample)/1e6
     cpsWindow = deltaCounts / windowSec
     blended = cpsWindow  // Δεν έχουμε αξιόπιστο cpsEdge
     filtered = EMA(blended)
     positionAccumulator += deltaCounts  // Συνολική θέση
     publish(positionAccumulator, filtered)
     lastSample = now
```

---
## 7. Βήμα-Βήμα Παράδειγμα (ISR Mode)
Υποθέσεις: PPR=1024, 4x decode → 4096 counts/rev, `SPEED_SAMPLE_US = 10000` (10ms).

1. Εντός 10ms πέρασαν 256 counts (≈ 1/16 περιστροφή).  
2. `deltaCounts = 256`, `windowSec = 0.010`, `cpsWindow = 256 / 0.010 = 25600 cps`.
3. Τελευταία edge διαστήματα ~39µs → `cpsEdge ≈ 1 / 0.000039 = 25641 cps`.
4. `absWindow > 1000` → high speed path → `blended = 0.7*25641 + 0.3*25600 ≈ 25629 cps`.
5. EMA (α=0.2): `filtered = 0.2*25629 + 0.8*prevFiltered`.  
6. Εκτυπώνεται: `Pos= <τρέχουσα_συσσωρευτική_θέση> cps=25629 rpm= (cps / countsPerRev * 60)`.

RPM υπολογισμός: `rpm = cps / 4096 * 60` → `≈ 25629 / 4096 * 60 ≈ 375.4 rpm`.

---
## 8. Παράδειγμα (Low Speed)
Σε 10ms περνούν 5 counts:  
- `cpsWindow = 5 / 0.010 = 500 cps` (<1000) αλλά >10.  
- Edge intervals ανομοιόμορφα (π.χ. jitter).  
- Blend ζώνης μέσης ταχύτητας: 50/50 (ή fallback).  
- Αν είχαμε μόνο 1 count σε 10ms → `cpsWindow=100 cps` (πολύ jitter στο edge) → παραμένει σταθερό λόγω averaging.

---
## 9. Παράδειγμα (Very Low Speed)
Σε 10ms 0 counts (σταματημένος άξονας).  
- `cpsWindow=0`, `absWindow<10` → blended=0 (καθαρό).  
- Edge method δεν έχει νέο edge → cpsEdge=0.  
- Φίλτρο κρατά ομαλή μετάβαση.

---
## 10. Πλεονεκτήματα Dual Method
| Περιοχή | Στόχος | Επιλογή |
|---------|--------|---------|
| Πολύ χαμηλή | Σταθερότητα | Window 100% |
| Ενδιάμεση | Εξισορρόπηση latency / jitter | Μείξη 50/50 |
| Υψηλή | Ταχεία απόκριση | 70% Edge / 30% Window |

Το adaptive blending αποφεύγει "θόρυβο" στις άκρες και αργή απόκριση στο κέντρο.

---
## 11. EMA Smoothing
Η ταχύτητα (`blended`) περνά από EMA:  
`filtered_t = α * blended_t + (1-α) * filtered_{t-1}`  
Μικρό α → πιο smooth, μεγάλο α → πιο γρήγορη απόκριση.

---
## 12. Μετάβαση σε PCNT Fallback
Αν ενεργοποιήσεις PCNT build flag (ή ρυθμίσεις) και δεν θες ISR:  
- Απενεργοποιείς edge decoding.  
- Κώδικας velocity απλοποιείται (βλέπε §6).  
- Adaptive thresholds παραμένουν αλλά πρακτικά όλα οδηγούν σε window.

---
## 13. Έλεγχος Ορθότητας
1. Επιβεβαίωσε counts/rev = 4 * PPR.  
2. Μέτρησε cps / rpm σε γνωστή περιστροφή (π.χ. 1 rev/sec → cps ≈ 4096, rpm=60).  
3. Δες ότι σε σταμάτημα το cps πέφτει εξομαλυμένα στο 0.  
4. Σε απότομη αλλαγή ταχύτητας, edge συνιστώσα δίνει γρήγορη μεταβολή.

---
## 14. Troubleshooting
| Σύμπτωμα | Πιθανή Αιτία | Λύση |
|----------|--------------|------|
| Θόρυβος σε low speed | Πολύ μικρό window | Αύξησε `SPEED_SAMPLE_US` |
| Αργή απόκριση σε accel | Πολύ μεγάλο window ή α μικρό | Μείωσε window / αύξησε α |
| Λάθος κατεύθυνση | Αντιστροφή A/B | Swap στα καλώδια ή invert flag |
| Jitter high speed | ISR overload | PCNT mode ή optimize ISR |
| Counts drop | Θόρυβος καλωδίωσης | Shield, pull-ups, debounce |

---
## 15. TL;DR
- Θέση: increment/decrement ανά quadrature βήμα.  
- Ταχύτητα: window (σταθερό) + edge (γρήγορο) → adaptive blend + EMA.  
- PCNT: μόνο window.  
- Thresholds 10 / 1000 cps επιλέγουν στρατηγική.  
- `SPEED_SAMPLE_US` ρυθμίζει ρυθμό/latency.

---
(Τεκμηρίωση βασισμένη στον υπάρχοντα κώδικα `encoder.cpp`, `config.h` και στα tutorials.)
