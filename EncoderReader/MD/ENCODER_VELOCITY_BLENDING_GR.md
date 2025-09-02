# Απλή Γραμμική Εξήγηση: Πώς Παράγεται η Τελική Ταχύτητα Encoder

## Σκοπός
Να δείξει με καθαρά βήματα πώς από τα σήματα A/B φτάνουμε στην έξοδο `cps` και `rpm` όταν χρησιμοποιούμε *και* Window Method *και* Edge Method (ISR) μαζί.

---
## 1. Είσοδοι
- Κανάλια A, B (Quadrature)
- (Προαιρετικά Z)
- Χρονός `micros()` από ESP32

---
## 2. Εσωτερικές Μεταβλητές
| Όνομα | Ρόλος |
|-------|------|
| `positionCounter` | Συνολική θέση (counts) |
| `lastSamplePos` | Θέση στην αρχή προηγούμενου window |
| `lastSampleTime` | Χρόνος αρχής προηγούμενου window |
| `prevEdgeTime` | Χρόνος προηγούμενης ακμής (ISR) |
| `lastEdgeInterval` | Διάρκεια μεταξύ δύο ακμών |
| `filteredVelocity` | Φιλτραρισμένη τελική ταχύτητα (EMA) |
| `SPEED_SAMPLE_US` | Διάρκεια window (π.χ. 10000 μs) |

---
## 3. Δύο Πηγές Ταχύτητας
### A. Window Method
Υπολογίζεται κάθε φορά που περάσει το χρονικό παράθυρο:
```
windowSec = (now - lastSampleTime)/1e6
deltaCounts = positionCounter - lastSamplePos
cpsWindow = deltaCounts / windowSec
```
Ενημέρωση δεικτών: `lastSamplePos = positionCounter`, `lastSampleTime = now`.

### B. Edge Method (ISR)
Κάθε ακμή:
```
ISR:
  read A,B -> step (+1 ή -1)
  positionCounter += step
  nowEdge = micros()
  edgeInterval = nowEdge - prevEdgeTime
  prevEdgeTime = nowEdge
```
Όταν χρειαζόμαστε ταχύτητα edge:
```
edgeIntervalSec = edgeInterval / 1e6
cpsEdge = (edgeIntervalSec>0)? 1/edgeIntervalSec : 0
```
Με πρόσημο ανάλογα με το step.

---
## 4. Blending (Adaptive)
```
absWindow = |cpsWindow|
absEdge = |cpsEdge|
if absWindow < 10:
    finalRaw = cpsWindow               # Πολύ χαμηλά: σταθερότητα
elif absWindow > 1000 and absEdge > 0:
    finalRaw = 0.7*cpsEdge + 0.3*cpsWindow  # Υψηλά: ταχύ edge
else:
    if cpsWindow>0 and cpsEdge>0:
        finalRaw = 0.5*(cpsWindow + cpsEdge)
    else:
        finalRaw = cpsWindow if cpsWindow!=0 else cpsEdge
```
PCNT mode: `finalRaw = cpsWindow` (δεν υπάρχει αξιόπιστο edge timing).

---
## 5. EMA Φίλτρο
```
filtered = alpha*finalRaw + (1-alpha)*filtered_prev
```
`alpha` π.χ. 0.2.

---
## 6. Έξοδοι
```
pos = positionCounter
cps = filtered
rpm = cps / countsPerRev * 60   # countsPerRev = 4 * PPR (με 4x)
```

---
## 7. Παράδειγμα High Speed
- 10ms window → deltaCounts=256 → cpsWindow=256/0.010=25600 cps
- Τελευταίο edge interval=39 μs → cpsEdge ≈ 25641 cps
- absWindow>1000 → high path → finalRaw ≈ 0.7*25641 + 0.3*25600 ≈ 25629 cps
- EMA (α=0.2, prev=25000) → filtered ≈ 25126 cps
- rpm ≈ 25126 / 4096 * 60 ≈ 368 rpm

---
## 8. Παράδειγμα Low Speed
- 10ms window → deltaCounts=2 → cpsWindow=200 cps
- Edge intervals άνισα (π.χ. 4ms & 6ms) → cpsEdge 250 & 166 → τρέχον 166 cps
- Μεσαία ζώνη → finalRaw = (200 + 166)/2 = 183 cps
- EMA λειαίνει.

---
## 9. Γιατί Λειτουργεί
- Window: καθαρή μέση τιμή (χαμηλό jitter) σε αργές/μέτριες ταχύτητες.
- Edge: μηδενικό latency σε επιτάχυνση/επιβράδυνση υψηλών ταχυτήτων.
- Blending: διαλέγει τη σωστή ισορροπία.
- EMA: αποφεύγει "τρέμουλο" στην οθόνη.

---
## 10. TL;DR
ISR → "στιγμιαία" ταχύτητα.  Window → μέση ταχύτητα.  Κανόνας → συνδυασμός ανά περιοχή ταχύτητας.  Τελικό → EMA.
