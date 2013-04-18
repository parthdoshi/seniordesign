
from __future__ import division
import sqlite3

def get_min(string):
    h, m, _ = string.split(":")
    return 60 * int(h) + int(m)

def get_str(mins):
    h = int(mins / 60) % 24
    m = mins % 60
    return "%02d:%02d:00" % (h, m)

c = sqlite3.connect('final.db')
c.create_function('mins', 1, get_min)
s = c.cursor()

print "made db"
s.execute('SELECT route_id, short_name FROM routes')
names = dict(s.fetchall())
print "made name dict"
s.execute('SELECT short_name, total FROM capacity')
capacity = dict(s.fetchall())
print "made capacity dict"

#time,baseline
baseline = dict(l.strip().split(',') for l in open('times.csv'))
print "made baseline dict1"
b2 = {b: 0 for b in baseline.keys()}

for i in xrange(60 * 24):
    string = get_str(i)
    s.execute('SELECT count(departure) from links where departure<? and '
              'arrival>=?',
              (string, string))
    count = int(s.fetchone()[0])
    try:
        b = int(baseline[string]) / count
    except ZeroDivisionError:
        print string + " got ZeroDivisionError"
    else:
        b2[string] += b
        print string + " worked"
print "made baseline dict2"

# origin, dest, departure, arrival, route_id, duration, capacity, baseline
s.execute('SELECT * from links')
output = []
with open('links.csv', 'wt') as f:
    for line in s.fetchall():
        line = list(line)
        line[6] = capacity[names[line[4]]]
        start = get_min(line[2])
        line[7] = int(sum(b2[get_str(i + start)] for i in xrange(line[5])))
        output.append(','.join(map(str, line)))

open('out.csv', 'w').write('\n'.join(output))
print "wrote out.csv"






