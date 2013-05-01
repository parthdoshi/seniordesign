
from __future__ import division
import sqlite3

def get_min(string):
    h, m, _ = string.split(":")
    return 60 * int(h) + int(m)

def get_str(mins):
    h = int(mins / 60) % 24
    m = mins % 60
    return "%02d:%02d:00" % (h, m)

class RidershipData:

    # DATA IN THOUSANDS
    AVG_DAILY_P = 830
    AVG_WEEKDAY_P = 1150
    AVG_WEEKEND_P = int((7 * AVG_DAILY_P - 5 * AVG_WEEKDAY_P) / 2)
    YEAR_PASSENGER_MILES = int(1526.795 * 1000)
    AVG_DAILY_PM = YEAR_PASSENGER_MILES / 365
    AVG_WEEKDAY_PM = int(AVG_DAILY_PM * AVG_WEEKDAY_P / AVG_DAILY_P)
    AVG_WEEKEND_PM = int(AVG_DAILY_PM * AVG_WEEKEND_P / AVG_DAILY_P)

TOTAL_RIDERSHIP = ??

PER_BLOCK = [
    ("00:00:00", 0),
    ("06:00:00", .035 * TOTAL_RIDERSHIP),
    ("09:00:00", .215 * TOTAL_RIDERSHIP),
    ("12:00:00", .155 * TOTAL_RIDERSHIP),
    ("15:00:00", .18 * TOTAL_RIDERSHIP),
    ("18:00:00", .26 * TOTAL_RIDERSHIP),
    ("21:00:00", .105 * TOTAL_RIDERSHIP),
    ("24:00:00", .055 * TOTAL_RIDERSHIP)
    ]

c = sqlite3.connect('final.db')
c.create_function('mins', 1, get_min)
s = c.cursor()

BASELINE_PCT = {}

for (t1, p1), (t2, p2) in zip(PER_BLOCK, PER_BLOCK[1:]):
    s.execute('SELECT sum(duration * capacity) '
              'FROM links '
              'WHERE departure>? and arrival<?',
              (t1, t2))
    pass_mins = s.fetchone()[0]
    s.execute('SELECT departure, duration, capacity '
              'FROM links '
              'WHERE departure < ? AND arrival BETWEEN ? AND ?',
              (t1, t1, t2))
    cutoff = get_min(t1)
    pass_mins += sum((get_min(dep) - cutoff) * du * ca
                     for dep, du, ca in s.fetchall())
    s.execute('SELECT departure, duration, capacity '
              'FROM links '
              'WHERE departure BETWEEN ? AND ? AND arrival >?',
              (t1, t2, t2))
    cutoff = get_min(t2)
    pass_mins += sum((cutoff - get_min(dep)) * du * ca
                     for dep, du, ca in s.fetchall())
    BASELINE_PCT[get_min(t1) / 180] = p2 / pass_mins
    print "made block %s - %s" % (t1, t2)

print "made per block map"

BASELINE_PCT[1] = BASELINE_PCT[0]

def get_pct(start, end):
    t1 = get_min(start) / 180
    t2 = get_min(end) / 180
    p1 = BASELINE_PCT[int(t1) % 8]
    p2 = BASELINE_PCT[int(t2) % 8]
    try:
        return ((t2 - int(t2)) * p2 + (int(t2) - t1) * p1) / (t2 - t1)
    except ZeroDivisionError:
        return p1

# origin, dest, departure, arrival, route_id, duration, capacity, baseline
s.execute('SELECT * from links')
output = []
for line in s.fetchall():
    line = list(line)
    start = get_min(line[2])
    line[7] = int(get_pct(line[2], line[3]) * line[6] + .5)
    output.append(','.join(map(str, line)))

open('out.csv', 'w').write('\n'.join(output))
print "wrote out.csv"






