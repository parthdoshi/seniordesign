import csv
import datetime
from datetime import date
from datetime import timedelta
import urllib2
import json

def get_next_home_game():
    """ Get next Philadelphia Phillies home game given schedule.csv as input """
    t = date.today()

    l = []
    csvfile = open('schedule.csv', 'rU')
    reader = csv.reader(csvfile, delimiter=',')
    for row in reader:
        if row[2] == 'Home':
            mdy = row[1].split('/')
            #print mdy, row[2]
            d = datetime.date(int(mdy[2]), int(mdy[0]), int(mdy[1]))
            l.append((d, row[5]))
    
    (mindate, time) = (t, 0)
    mindelta = timedelta.max
    
    for v in l:
        d = v[0]
        if d >= t:
            delta = d - mindate
            #print d, mindate, mindelta
            if delta < mindelta:
                (mindate, time) = (d, v[1])
                mindelta = delta
                #print (mindate, int(time))
    
    get_weather(mindate, int(time))

def get_weather(date, time):
    """ Get weather for a given date at a given hour (int) """
    
    #print date, time
    query = ("http://api.wunderground.com/api/4c3fa24ce9b89b4c/hourly10day/q/PA/19148.json")
    
    url = urllib2.urlopen(query)
    resp = json.loads(url.read())
    #f = open('resp.txt','w')
    #json.dump(resp, f)
    #f.close()
    
    str = "%s:00 PM EDT on %s %s, %s"
    comp = str % (time % 12, date.strftime("%B"), date.day, date.year)
    #print compx`
    
    #f = open('resp.txt', 'r')
    #resp = json.loads(f.read())
    
    (far, cel, cond, image) = ("", "", "", "")
    
    for var in resp['hourly_forecast']:
        if var['FCTTIME']['pretty'] == comp:
            (far, cel, cond, image) = (var['temp']['english'],
                var['temp']['metric'], var['condition'], var['icon_url'])
    
    #f.close()
    
    g = open('weather.csv', 'w')
    tup = (far, cel, cond, image, comp)
    g.write(','.join(tup))
    g.close()

get_next_home_game()