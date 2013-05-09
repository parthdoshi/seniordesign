import csv

def calculate_emissions(mpg, fuel_type, zcode, idling):
    """ calculate_emissions(21, 'diesel', 19104) """
    epg = 8887
    IDLING_TIME = idling
    IDLING_CO2 = 28.3
    if fuel_type == 'diesel':
        epg = 10180
    epm = epg/mpg

    csvfile = open('results.csv', 'rU')
    reader = csv.reader(csvfile, delimiter=',')
    
    meter_dist = 0
    for row in reader:
        if int(row[0]) == zcode:
            meter_dist = int(row[1].split('.')[0])

    mile_dist = meter_dist * 0.000621371

    moving_emission = epm * mile_dist
    
    idling_emission = IDLING_TIME * IDLING_CO2
    
    #print moving_emission, idling_emission, moving_emission + idling_emission
    
    return moving_emission + idling_emission # grams of CO2

calculate_emissions(21, 'diesel', 19104, 20)