
"""
This module queries the google maps API to
obtain driving or public transit directions
to the stadium from all Philadelphia area
zip codes. It uses the results to calculate
total travel times and total distances.
"""

from __future__ import division
import urllib2
import urllib
import sys
import json
import time

## Stadium data:
LAT = 39.90610239999999
LNG = -75.16652580
LATLNG = "%s,%s" % (LAT, LNG)
ZIP = 19148

def get_json(zipcode):
    base = "http://maps.googleapis.com/maps/api/directions/json?"
    params = {
        'origin': zipcode,
        'destination': LATLNG,
        'mode': 'transit',
        'arrival_time': 1365953797,
        'sensor': 'false'}
    final_url = base + urllib.urlencode(params).replace('%2C', ',')
    url = urllib2.urlopen(final_url)
    return url.read()

def parse_json(raw):
    top = json.loads(raw)
    try:
        route = top['routes'][0]
    except IndexError:
        if top['status'] == 'OVER_QUERY_LIMIT':
            time.sleep(1)
            raise ValueError
        elif top['status'] == 'ZERO_RESULTS':
            raise KeyError
        elif top['status'] == 'NOT_FOUND':
            raise KeyError
        else:
            print raw
            raise
    tot_dist = 0
    tot_time = 0
    for leg in route['legs']:
        tot_dist += leg['distance']['value']
        tot_time += leg['duration']['value']
    return tot_dist, tot_time / 60

def main():
    with open('results.csv', 'w') as f:
        f.write('zip,meters,minutes')
        for i in range(19101, 19161):
            print i
            failure = True
            while failure:
                raw = get_json(i)
                try:
                    d, t = parse_json(raw)
                    res = "%d,%f,%f" % (i, d, t)
                    failure = False
                except ValueError:
                    pass
                except KeyError:
                    res = "%d,-,-" % i
                    failure = False
            f.write(res + '\n')

main()
