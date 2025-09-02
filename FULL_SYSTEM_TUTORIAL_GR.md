# Πλήρες Tutorial Αρχιτεκτονικής Συστήματος ESP32 Encoder + Python GUI

(Για αρχάριους με προοδευτική εμβάθυνση – από το hardware μέχρι το GUI και την εξαγωγή δεδομένων)

---
## Περιεχόμενα
1. Εισαγωγή – Τι πρόβλημα λύνει το σύστημα
2. Γενική Εικόνα Αρχιτεκτονικής (High-Level Overview)
3. Hardware & Encoder Βασικές Έννοιες
4. Firmware ESP32 (Arduino / PlatformIO) – Δομή & Modules
5. Βρόχος Μέτρησης Παλμών & Υπολογισμός Ταχύτητας
6. Πρωτόκολλο Επικοινωνίας Σειριακής (Serial Protocol)
7. Python Εφαρμογή – Αρχιτεκτονική Modules
8. Νήματα (Threads) & Ροή Δεδομένων End-to-End
9. Βήμα-Βήμα Σενάρια (Connect, Run, Tare, Export)
10. Διαχείριση Απόδοσης (Performance) & Βελτιστοποιήσεις
11. Αντιμετώπιση Σφαλμάτων & Αξιοπιστία
12. Επεκτασιμότητα & Πώς Προσθέτω Νέα Λειτουργία
13. Συχνά Λάθη & Troubleshooting
14. Λεξικό Όρων (Glossary)
15. Γρήγορος Πίνακας Αναφοράς (Cheat Sheet)

---
## 1. Εισαγωγή – Τι πρόβλημα λύνει το σύστημα
Το σύστημα καταγράφει σε πραγματικό χρόνο τη θέση (pulses) ενός περιστροφικού encoder (Omron E6B2-CWZ6C) συνδεδεμένου σε ESP32-S3 και προαιρετικά μία μετρούμενη δύναμη (force/weight) από ξεχωριστή πηγή (π.χ. load cell firmware ή δεύτερη ροή). Ο μικροελεγκτής διαβάζει γρήγορα και αξιόπιστα παλμούς (με hardware PCNT + interrupts fallback) και στέλνει τα δεδομένα στη Python GUI εφαρμογή, η οποία:
- Εμφανίζει ζωντανά pulses, διαφορές (delta), υπολογισμένη ταχύτητα (αν ενσωματωθεί) και δύναμη.
- Τα αποθηκεύει προσωρινά σε buffer.
- Τα εμφανίζει σε πίνακα & γράφημα.
- Επιτρέπει εξαγωγή σε Excel.

Στόχος: Ένας αρχάριος να κατανοήσει ΟΛΗ τη ροή.

---
## 2. Γενική Εικόνα Αρχιτεκτονικής (High-Level Overview)
```
┌──────────────────────────────────────────────────────────────┐
│                        HARDWARE LAYER                       │
│  Encoder (A,B) → ESP32-S3 GPIO (PCNT / ISR) → Μετρητές       │
└──────────────────────────────────────────────────────────────┘
            │ pulses + timestamp (υπολογισμός velocity) 
            ▼
┌──────────────────────────────────────────────────────────────┐
│                    FIRMWARE (ESP32)                         │
│  encoder.cpp / encoder.h: decode + position + delta         │
│  commands.cpp: εντολές (TARE κλπ)                           │
│  display.cpp (αν υπάρχει οθόνη)                             │
│  main (EncoderReader.ino): loop -> διαβάζει & τυπώνει lines │
└──────────────────────────────────────────────────────────────┘
            │ Serial lines (π.χ. "Pos=12345 Δ=12 Force=1.234")
            ▼
┌──────────────────────────────────────────────────────────────┐
│                       USB SERIAL PORT                       │
└──────────────────────────────────────────────────────────────┘
            │ bytes
            ▼
┌──────────────────────────────────────────────────────────────┐
│                     PYTHON APPLICATION                       │
│  serial_handler.py (Thread) → raw lines                      │
│  data_parser.py → ταξινόμηση/parser                         │
│  data_models.py (Sample, Buffer)                             │
│  gui_components.py / encoder_gui.py                          │
│      - Πίνακας - Γράφημα - Κουμπιά                           │
│  data_export.py → Excel                                      │
└──────────────────────────────────────────────────────────────┘
            │ user actions / visualization
            ▼
┌──────────────────────────────────────────────────────────────┐
│                       ΤΕΛΙΚΟΣ ΧΡΗΣΤΗΣ                       │
└──────────────────────────────────────────────────────────────┘
```

---
## 3. Hardware & Encoder Βασικές Έννοιες
- Quadrature Encoder: 2 κανάλια (A, B) με φάση 90°. Επιτρέπει ανίχνευση κατεύθυνσης & βήματος.
- Pulses per Revolution (PPR): Πόσοι παλμοί ανά πλήρη περιστροφή (π.χ. 360, 600, 1024). Σημαντικό για υπολογισμό γωνίας ή ταχύτητας.
- ESP32-S3 PCNT (Pulse Counter): Hardware block που μετρά παλμούς με ελάχιστο CPU overhead.
- Interrupts Fallback: Αν χρειαστεί, interrupts στα κανάλια A/B για χειροκίνητη αποκωδικοποίηση.
- Debouncing / Filtering: Στον κώδικα μπορεί να γίνει λογική για καθαρισμό (συνήθως ο PCNT βοηθά ήδη).

---
## 4. Firmware ESP32 – Δομή & Modules
Κύρια αρχεία (στον φάκελο `EncoderReader` ή `ArduinoEncoderSketch`):
- `config.h`: Pins, constants (π.χ. ENCODER_PPR, REPORT_INTERVAL_MS).
- `encoder.h / encoder.cpp`: Λογική ανάγνωσης παλμών, υπολογισμός διαφοράς, αποθήκευση τρέχουσας τιμής, reset (tare).
- `commands.h / commands.cpp`: Ερμηνεία εισερχόμενων σειριακών command strings (π.χ. "TARE").
- `display.*` (προαιρετικό): Εμφάνιση σε OLED ή Serial debug.
- `EncoderReader.ino` (main): setup() -> init modules, loop() -> περιοδική ανάγνωση & αποστολή.

### 4.1 Ροή στο `setup()`
1. Αρχικοποίηση σειριακής: `Serial.begin(115200)`
2. Ρύθμιση PCNT ή pin interrupts για encoder.
3. Μηδενισμός counters.
4. (Αν υπάρχει display) init οθονών.
5. Μήνυμα “READY”.

### 4.2 Ροή στο `loop()`
Κάθε κύκλο ή ανά χρονικό διάστημα:
1. Διαβάζει τρέχον count από encoder.
2. Υπολογίζει delta = current - previous.
3. Προαιρετικά υπολογίζει γωνία ή velocity (pulses / Δt).
4. Διαβάζει προαιρετικά force (αν ενσωματωθεί sensor).
5. Συνθέτει μία γραμμή κειμένου: `Pos=12345 Δ=12 Force=1.234`.
6. `Serial.println(line)` → στέλνεται στον host.
7. Ελέγχει αν έχει ληφθεί command (Serial.available()) → parse.

### 4.3 Command Handling
- Command: "TARE" → μηδενίζει εσωτερικό offset ώστε `position = 0`.
- Μπορούν να προστεθούν: "RATE?", "PPR?", "RESET".

---
## 5. Βρόχος Μέτρησης Παλμών & Υπολογισμός Ταχύτητας
Τρόποι:
1. **PCNT hardware**: Καταγράφει παλμούς χωρίς να φορτώνει CPU.
2. **Interrupt Quadrature**: ISR σε A/B transitions – υπολογισμός +1/-1.
3. **Υπολογισμός Velocity** (προαιρετικός):
   - Αποθηκεύουμε timestamp προηγούμενης μέτρησης.
   - velocity = (delta_pulses * 1000) / Δms  (pulses per second) → μετατροπή σε RPM: `rpm = (pulses_per_second * 60) / PPR`.

Παράδειγμα (ψευδοκώδικας):
```
last_count = read_counter()
last_time = millis()
loop:
  now = millis()
  if (now - last_report >= REPORT_INTERVAL_MS):
     current = read_counter()
     delta = current - last_count
     dt = now - last_time
     velocity = (delta * 1000.0) / dt
     rpm = (velocity * 60.0) / PPR
     print("Pos=... Δ=... Vel=... RPM=...")
     last_count = current
     last_time = now
```

---
## 6. Πρωτόκολλο Επικοινωνίας Σειριακής (Serial Protocol)
Αποστέλλονται lines (ASCII) με newline `\n`.
Τυπική μορφή:
```
Pos=12345 Δ=12 Force=1.234
```
Δυνατές παραλλαγές:
- Μόνο pulses: `Pos=12345 Δ=12`
- Με velocity: `Pos=12345 Δ=12 Vel=456.7`
- Force/Weight ως χωριστή γραμμή: `Force=1.234`

Η Python πλευρά αναγνωρίζει patterns:
- Γραμμή που ξεκινά με `pos=` → πακέτο θέσης.
- Γραμμή που ξεκινά με `force=` ή `weight=` → ενημέρωση δύναμης.

Στόχος: Απλό, ανθεκτικό σε parsing (χαμηλή πολυπλοκότητα).

---
## 7. Python Εφαρμογή – Αρχιτεκτονική Modules
Φάκελος `python_client` (ή ενσωματωμένο variant στον `EncoderReader`).

| Αρχείο | Ρόλος |
|--------|------|
| `serial_handler.py` | Thread που διαβάζει τη σειριακή πόρτα και στέλνει κάθε γραμμή στον parser callback. |
| `data_parser.py` | Εντοπίζει τι τύπος γραμμής είναι, εξάγει pulses, delta, force. |
| `data_models.py` | Ορίζει `Sample` (dataclass), buffer, thread-safe λογικές αποθήκευσης. |
| `data_export.py` | Εξαγωγή δεδομένων σε Excel (xlsx) ή CSV. |
| `gui_components.py` | Δομικά κομμάτια UI (πλαίσιο, treeview, plot). |
| `encoder_gui.py` | Κύρια κλάση GUI: state, κουμπιά, timers, σύνδεση / αποσύνδεση. |
| `config.py` | Σταθερές, ρυθμίσεις (refresh rate, όρια plot). |

### 7.1 Βασικές Κλάσεις
- `SerialReader(Thread)`: Ανοίγει `serial.Serial`, loop: `readline()`, καλεί callback.
- `Sample`: `t` (χρόνος), `pulses`, `delta`, `force`.
- `DataBuffer`: λίστα δειγμάτων + μεθόδους προσθήκης.
- `EncoderGUI`: Συντονίζει: state (running, connected), timers, events.

### 7.2 GUI Loop vs Background Thread
- GUI Thread: Tkinter mainloop → χειρίζεται redraw, user clicks.
- Serial Thread: Διαβάζει, δεν αγγίζει widgets (χρησιμοποιεί `after` ή buffer + mutex).

---
## 8. Νήματα (Threads) & Ροή Δεδομένων End-to-End
```
[ENCODER HARDWARE]
    │ (ηλεκτρικοί παλμοί)
    ▼
[PCNT / ISR] (Firmware)
    │ position, delta
    ▼
[Serial.println("Pos=... Δ=... Force=...")]
    │ bytes μέσω USB
    ▼
[PC Host Driver]
    │ virtual COM port
    ▼
[SerialReader Thread - Python]
    │ line strings
    ▼
[data_parser.py]
    │ pulses, delta, force
    ▼
[DataBuffer + Sample list]  ← (protected by mutex)
    │ periodic copy (GUI timer)
    ▼
[GUI: Table + Plot]
    │ user interactions
    ▼
[Commands (TARE)] → γράφονται πίσω στη Serial → Firmware εκτελεί → νέα μέτρηση
```

### 8.1 Λεπτομερής Ακολουθία (Sequence Diagram)
```
User          GUI(Main)        SerialThread      Firmware(ESP32)     Encoder
 |               |                  |                |                |
 |  Launch app   |                  |                |                |
 |-------------->| build widgets    |                |                |
 |  Select Port  |                  |                |                |
 |-------------->| set var          |                |                |
 |  Connect      |                  |  open port     |                |
 |-------------->| start thread ----|--------------->|   ready        |
 |               |                  |  read lines    |                |
 |               |<-- after(...) ---|                |                |
 |               | update table/plot|                |                |
 |  Click Start  |                  |                |                |
 |-------------->| running=True     |                |                |
 |               |                  |                | read pulses    |<- mechanical rotation
 |               |                  |                | Serial.println |-> "Pos=... Δ=..."
 |               |                  |<---------------|                |
 |               | after_idle(update)                |                |
 |               | update UI                         |                |
 |  TARE         | write("TARE")    |--------------->| reset counter  |
 |-------------->|                  |                |                |
 |  Stop         | running=False    |                | continue idle  |
 |-------------->|                  |                |                |
 | Export        | gather samples   |                |                |
 |-------------->| write Excel      |                |                |
 | Disconnect    | stop thread      | close serial   |                |
 |-------------->|                  |                |                |
```

---
## 9. Βήμα-Βήμα Σενάρια
### 9.1 Σενάριο: Πρώτη Εκκίνηση
1. Συνδέω ESP32 με USB.
2. Ανοίγω Python GUI.
3. Στο dropdown COM επιλέγω τη θύρα.
4. Πατάω Connect → ανοίγει serial thread.
5. Πατάω Start → αρχίζει συλλογή.
6. Περιστρέφω τον άξονα → pulses αυξάνονται.
7. Τα δεδομένα εμφανίζονται σε πίνακα & plot.

### 9.2 Σενάριο: TARE (Μηδενισμός)
1. Άξονας σε επιθυμητή θέση αναφοράς.
2. Πατάω TARE → στέλνεται "TARE".
3. Firmware θέτει internal offset.
4. Επόμενη γραμμή `Pos=0`.

### 9.3 Σενάριο: Force Lines
1. Αν firmware ή δεύτερο σύστημα στέλνει `Force=1.234`.
2. Serial thread το λαμβάνει.
3. Parser ενημερώνει `current_force`.
4. Επόμενες encoder γραμμές μπορούν να συνδυαστούν με την τελευταία τιμή force.

### 9.4 Σενάριο: Export
1. Πατάω Export.
2. GUI παίρνει αντίγραφο των samples (με mutex).
3. Δημιουργεί DataFrame → .xlsx.
4. Εμφανίζεται μήνυμα επιτυχίας.

---
## 10. Διαχείριση Απόδοσης (Performance)
| Σημείο | Βελτίωση |
|--------|----------|
| PCNT Hardware | Μειώνει CPU load σε υψηλά RPM. |
| Decimation Plot | Περιορίζει σημεία (π.χ. 4000) για ομαλό redraw. |
| Mutex + Copy | GUI δεν μπλοκάρει το serial thread. |
| Χρήση after() | Αποφυγή blocking στον κύριο βρόχο Tkinter. |
| Απλό Protocol | Ελάχιστη CPU κατανάλωση στο parsing. |

### 10.1 Memory Strategy
- Buffer κρατά λίστα δειγμάτων.
- Εάν γίνει πολύ μεγάλη: μπορείς να εφαρμόσεις pruning (π.χ. διαγράφεις παλιά).

---
## 11. Αντιμετώπιση Σφαλμάτων & Αξιοπιστία
| Πρόβλημα | Αίτιο | Λύση |
|----------|-------|------|
| Δεν εμφανίζονται pulses | Λάθος COM port ή δεν τρέχει firmware | Έλεγξε `Serial Monitor` με άλλο εργαλείο. |
| Random disconnect | Καλώδιο USB/ισχύς | Άλλαξε καλώδιο, έλεγξε drivers. |
| Force δεν ενημερώνεται | Δεν στέλνονται γραμμές Force= | Έλεγξε firmware ή δεύτερη πηγή. |
| Plot "πηδά" | Απότομες τιμές ή μηδενισμός (TARE) | Αναμενόμενο. |
| Export αποτυγχάνει | Αρχείο ανοιχτό σε Excel | Κλείσε το αρχείο & ξανά. |

### 11.1 Ασφαλές Κλείσιμο
- Πατάω Disconnect ή κλείνω το παράθυρο.
- Serial thread: stop event → join.
- Αποφυγή εξαιρέσεων Tkinter.

---
## 12. Επεκτασιμότητα & Πώς Προσθέτω Νέα Λειτουργία
### 12.1 Προσθήκη Velocity στο Firmware
1. Υπολογίζεις delta/Δt.
2. Προσθέτεις στο print: `Vel=xxx`.
3. Στο Python parser: νέο key extraction.
4. Στο Sample: προσθήκη πεδίου (π.χ. `velocity`).
5. Επέκταση plot δεύτερης καμπύλης.

### 12.2 Νέα Εντολή (π.χ. SET_PPR 1024)
1. Firmware `commands.cpp`: parse → αλλάζει global ppr.
2. Αποστολή επιβεβαίωσης "OK".
3. Python: κουμπί που στέλνει `SET_PPR 1024\n`.

### 12.3 Plugin Pattern (π.χ. Αλγόριθμος Φιλτραρίσματος)
1. Νέο αρχείο `filter_plugin.py`.
2. Hook: μετά από προσθήκη sample.
3. GUI plugin manager το φορτώνει.

---
## 13. Συχνά Λάθη & Troubleshooting
| Λάθος | Εξήγηση |
|-------|----------|
| Αρχάριος μπλοκάρει GUI με time.sleep | Πρέπει να χρησιμοποιεί `after()` |
| Προσπάθεια ενημέρωσης widget από serial thread | Tkinter δεν είναι thread-safe |
| Λανθασμένο parsing (lowercase vs uppercase) | Κάνουμε `.lower()` πριν έλεγχο |
| Μηδενισμός ενώ συλλέγει → απότομο γράφημα | Είναι φυσιολογικό (restart baseline) |

---
## 14. Λεξικό Όρων (Glossary)
- **Pulses**: Αύξηση/μείωση με κάθε βήμα encoder.
- **Delta**: Διαφορά παλμών από προηγούμενη μέτρηση.
- **Velocity**: Ρυθμός μεταβολής pulses/χρόνο.
- **RPM**: Περιστροφές ανά λεπτό.
- **PCNT**: Pulse Counter hardware μονάδα ESP32.
- **TARE**: Μηδενισμός τρέχουσας θέσης (reset offset).
- **Thread**: Παράλληλη διεργασία μέσα στο πρόγραμμα.
- **Mutex**: Μηχανισμός για αμοιβαίο αποκλεισμό (ασφάλεια δεδομένων). 
- **Decimation**: Δειγματοληψία κάθε Νου δείγματος για μείωση φόρτου.
- **Callback**: Συνάρτηση που καλείται όταν συμβεί γεγονός.

---
## 15. Γρήγορος Πίνακας Αναφοράς (Cheat Sheet)
| Ενέργεια | Τι κάνω | Τι συμβαίνει μέσα |
|----------|---------|--------------------|
| Εκκίνηση | Ανοίγω GUI | Φορτώνει widgets, timers |
| Επιλογή COM | Dropdown | Επιλογή θύρας για serial thread |
| Connect | Κουμπί | Ανοίγει θύρα, ξεκινά thread ανάγνωσης |
| Start | Κουμπί | `running=True`, αρχίζει καταγραφή δειγμάτων |
| Περιστροφή | Κίνηση άξονα | Firmware στέλνει `Pos=` γραμμές |
| TARE | Κουμπί | Αποστολή "TARE" → Firmware μηδενίζει offset |
| Force Update | Κατά την είσοδο | Parser αποθηκεύει current_force |
| Export | Κουμπί | Αντιγραφή buffer → Excel αρχείο |
| Disconnect | Κουμπί | Stop event → thread join |
| Exit | Κλείσιμο παραθύρου | Stop timers + thread + destroy |

---
## Τελική Σύνοψη
Από τον encoder μέχρι το Excel αρχείο, η αρχιτεκτονική βασίζεται σε καθαρές στρώσεις:
1. Hardware → firmware με PCNT/ISR.
2. Firmware → απλό, επεκτάσιμο πρωτόκολλο ASCII.
3. Python → modular (serial, parsing, data model, GUI, export).
4. Threading → ένας background αναγνώστης, GUI main loop, ασφαλής μεταφορά δεδομένων.
5. Visualization & Export → άμεση πληροφόρηση + ανάλυση offline.

Με την κατανόηση αυτής της ροής, μπορείς εύκολα:
- Να προσθέσεις νέα πεδία (π.χ. θερμοκρασία).
- Να αλλάξεις ρυθμούς ανανέωσης.
- Να βελτιώσεις φίλτρα/υπολογισμούς.
- Να μεταφέρεις την ίδια ιδέα σε άλλα αισθητήρια.

Καλή μελέτη & εξερεύνηση! 🚀
