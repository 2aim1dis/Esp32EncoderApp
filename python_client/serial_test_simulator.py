"""
serial_test_simulator.py

Simple simulator that emits serial lines like the firmware and demonstrates parsing
and buffering similar to the project's Python client. Useful to validate parser/GUI
without hardware.

Run: python python_client/serial_test_simulator.py

"""
import time
import re
from dataclasses import dataclass

LINE_RE = re.compile(r'Pos=(?P<pos>-?\d+)\s+cps=(?P<cps>[-\d.]+)\s+rpm=(?P<rpm>[-\d.]+)')

@dataclass
class Sample:
    t: float
    pos: int
    cps: float
    rpm: float

buffer = []

# simple parser (same logic as GUI)
def parse_line(line: str):
    m = LINE_RE.search(line)
    if not m:
        return None
    pos = int(m.group('pos'))
    cps = float(m.group('cps'))
    rpm = float(m.group('rpm'))
    s = Sample(time.time(), pos, cps, rpm)
    buffer.append(s)
    return s

# generator: simulate a velocity profile (accel, cruise, decel)
def generate_profile(counts_per_rev=4096):
    pos = 1000
    # phases: slow (200 cps), ramp to 5000 cps, cruise, ramp down
    phases = [ (0.5, 200), (1.0, 1000), (2.0, 5000), (1.0, 1000), (0.5, 200) ]
    for dur_s, cps in phases:
        end = time.time() + dur_s
        while time.time() < end:
            # compute delta for a short step (simulate report every 0.01s)
            dt = 0.01
            delta_counts = int(round(cps * dt))
            pos += delta_counts
            rpm = cps / counts_per_rev * 60.0
            line = f"Pos={pos} cps={cps:.2f} rpm={rpm:.2f}"
            s = parse_line(line)
            print(f"EMIT: {line}")
            if s:
                print(f"PARSED -> t={s.t:.3f} pos={s.pos} cps={s.cps:.1f} rpm={s.rpm:.2f}")
            time.sleep(dt)
    print('\nSimulation done. Buffer length:', len(buffer))

if __name__ == '__main__':
    print('Starting serial test simulator...')
    generate_profile()
