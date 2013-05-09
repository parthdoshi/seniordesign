#!/usr/local/bin/python
import cgi
import csv
import cgitb
from string import Template
import time
import urllib2
import json
import re
import resource
cgitb.enable()

def main():
    print "Content-type: text/html\n"
    form = cgi.FieldStorage() # parse query
    zipcode = '19104'
    if form.has_key("zipcode") and form["zipcode"].value != "":
        zipcode = form["zipcode"].value
    address = zipcode
    if form.has_key("address") and form["address"].value != "":
        address = form["address"].value
    mpg = 21
    if form.has_key("mpg") and form["mpg"].value != "":
        mpg = form["mpg"].value
    fuel_type = 'diesel'
    if form.has_key("fuel") and form["fuel"].value != "":
        fuel_type = form["fuel"].value
    # print "<h1>Hello", address, mpg, zipcode, "</h1>"

    emissions = calculate_emissions(mpg, fuel_type, zipcode, 20)

    # print "<h1>Hello", address, mpg, fuel_type, emissions, "</h1>"

    (car_dist, transit_dist, car_time, transit_time) = distances(zipcode)
    if not re.match("[0-9][0-9][0-9][0-9][0-9] *$", address):
        address += ", " +zipcode
    # body = open(result.part).read()
    part_temp = Template(open("result.part").read())
    body = part_temp.substitute(car_time=car_time, septa_time=transit_time, car_dist=car_dist,
            septa_dist=transit_dist, car_emmis=emissions, septa_emmis=0,
            car_cong=str(54), septa_cong=str(32), script=address_to_map(address))
    TEMPLATE = Template(open('template.html').read())
    html = TEMPLATE.substitute(title="Results", content=str(body))
    print html
	# print memory_usage()

    # print "<h1>Hello", car_dist, transit_dist, car_time, transit_time, "</h1>"

def calculate_emissions(mpg, fuel_type, zcode, idling):
    """ calculate_emissions(21, 'diesel', 19104, 20) """

    epg = 8887

    IDLING_TIME = idling

    IDLING_CO2 = 28.3

    if fuel_type == 'diesel':
        epg = 10180

    # print "<h1>Hello", mpg, "</h1>"
    epm = epg/int(mpg)

    # print epm, epg, mpg


    csvfile = open('cgi-bin/results_car.csv', 'rU')
    reader = csv.reader(csvfile, delimiter=',')
    
    meter_dist = 0
    for row in reader:
        if row[0] == zcode:
            meter_dist = int(row[1].split('.')[0])

    mile_dist = meter_dist * 0.000621371

    # print type(zcode), epm, mile_dist

    moving_emission = round(epm * mile_dist, 2)

    # print moving_emission, epm, mile_dist
    
    idling_emission = idling * IDLING_CO2
    
    #print moving_emission, idling_emission, moving_emission + idling_emission
    
    return moving_emission + idling_emission # grams of CO2

def distances(zcode):
    '''
        Takes in zipcode
        Outputs: (car_dist, transit_dist, car_time, transit_time)
    '''
    csvfile1 = open('cgi-bin/results_car.csv', 'rU')
    reader1 = csv.reader(csvfile1, delimiter=',')
    
    csvfile2 = open('cgi-bin/results_transit.csv', 'rU')
    reader2 = csv.reader(csvfile2, delimiter=',')
    
    car_dist = 0
    car_time = 0
    for row in reader1:
        # print row[0] == zcode
        if row[0] == zcode:
            car_dist = int(float(row[1]))
            car_time = int(float(row[2]))
    
    transit_dist = 0
    transit_time = 0
    for row in reader2:
        if row[0] == zcode:
            transit_dist = int(float(row[1]))
            transit_time = int(float(row[2]))

    return (car_dist, transit_dist, car_time + 30, transit_time)

def address_to_map(address):
    """ Needs input address: e.g. "3925 Walnut Street" """
    (lat, lng) = get_lonlat(address)
    #print lat, lng
    return gen_map(lat, lng)

def get_lonlat(address, rec=0):
    base = ("http://maps.googleapis.com/maps/api/geocode/json?"
            "address=%s&sensor=false")
    final_url = base % (address.replace(" ", "+"))
    
    url = urllib2.urlopen(final_url)
    resp = json.loads(url.read())
    try:
        loc = resp['results'][0]['geometry']['location']
        return (loc['lat'], loc['lng'])
    except KeyError:
        if resp['status'] == 'ZERO_RESULTS':
            raise ValueError('ZERO_RESULTS for %s' % (address))
        elif resp['status'] == 'NOT_FOUND':
            raise ValueError('%s NOT_FOUND' % (address))
        else:
            print resp
            raise
    except IndexError:
        if resp['status'] == 'OVER_QUERY_LIMIT':
            #print "Sleeping"
            if rec > 2:
                return 40,-79
            time.sleep(1)
            return get_lonlat(address, rec+1)
    except Exception:
        print resp
        raise

def gen_map(lat, lng):
    f1 = open('in.html', 'r')
    str = f1.read()
    f1.close()
    
    new_str = str % (lat, lng)
    #print new_str
    
    return new_str  # contains the html code to POST for the Map

main()