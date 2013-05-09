import time
import urllib2
import json

def address_to_html(address):
    (lat, lng) = get_match(address)
    print lat, lng
    generate_html(lat, lng)

def generate_html(lat, lng):
    f1 = open('in.html', 'r')
    str = f1.read()
    f1.close()
    
    new_str = str % (lat, lng)
    #print new_str
    
    f2 = open('out.html','w')
    f2.write(new_str)
    f2.close()

def get_match(address):
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
            print "Sleeping"
            time.sleep(1)
            return get_match(address)
    except Exception:
        print resp
        raise

address_to_html("3537 Walnut Street Philadelphia")