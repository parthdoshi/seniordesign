import csv

def distances(zcode):
    '''
        Takes in zipcode
        Outputs: (car_dist, transit_dist, car_time, transit_time)
    '''
    csvfile1 = open('results_car.csv', 'rU')
    reader1 = csv.reader(csvfile1, delimiter=',')
    
    csvfile2 = open('results_transit.csv', 'rU')
    reader2 = csv.reader(csvfile2, delimiter=',')
    
    car_dist = 0
    for row in reader1:
        print row
        if int(row[0]) == zcode:
            car_dist = int(float(row[1]))
            car_time = int(float(row[2]))
    
    transit_dist = 0
    for row in reader2:
        if int(row[0]) == zcode:
            transit_dist = int(float(row[1]))
            transit_time = int(float(row[2]))

    return (car_dist, transit_dist, car_time, transit_time)

distances(19160)
