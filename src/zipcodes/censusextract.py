
import re

class DataReader(object):

    ID_LINE_RE = re.compile("^ +([0-9]+) +"
                            "(-?0[.][0-9]+E[+]02) +"
                            "(-?0[.][0-9]+E[+]02)$")

    COORDS_RE = re.compile("^ +(-?0[.][0-9]+E[+]02) +"
                           "(-?0[.][0-9]+E[+]02)$")

    def __init__(self, filename):
        self.file = open(filename)
        self.current_id = None
        self.current_poly = []
        self.polys = {}

    def readline(self):
        line = self.file.readline()
        if not line:
            raise StopIteration
        line = line.rstrip('\n')
        if line == 'END':
            self.end_poly()
            return 1
        m = self.ID_LINE_RE.match(line)
        if m:
            self.start_poly(m.group(1))
            self.add_coords(*m.groups()[1:])
            return 1
        m = self.COORDS_RE.match(line)
        if m:
            self.add_coords(*m.groups())
            return 1
        try:
            id_ = int(line)
        except ValueError:
            pass
        else:
            self.start_poly(id_)
            return 1
        return 0

    def start_poly(self, id_):
        if id_ != -99999:
            self.current_id = int(id_)

    def end_poly(self):
        if self.current_id not in self.polys:
            self.polys[self.current_id] = []
        self.polys[self.current_id].append(tuple(self.current_poly))
        self.current_poly = []

    def add_coords(self, x, y):
        x = float(x)
        y = float(y)
        self.current_poly.append((x, y))

    def __iter__(self):
        return self

    def next(self):
        return self.readline()

class InfoReader(object):

    KEYS = ('ID', 'FIPS CODE(S)', 'NAME', 'LSAD', 'LSAD TRANSLATION')

    def __init__(self, filename):
        self.file = open(filename)
        self.current = {}
        self.data = {}

    def readline(self):
        line = self.file.readline()
        if not line:
            raise StopIteration
        line = line.rstrip('\n')
        i = len(self.current)
        if i == 0:
            self.current['ID'] = int(line.strip())
            return 1
        elif i < 5:
            self.current[self.KEYS[i]] = line.strip().strip('"')
            return 1
        else:
            self.close_entry()
            return not line.strip()

    def close_entry(self):
        self.data[self.current['ID']] = self.current
        if self.current['FIPS CODE(S)'] != self.current['NAME']:
            print "Difference at %d" % self.current['ID']
        self.current = {}

    def __iter__(self):
        return self

    def next(self):
        return self.readline()


class ZipCodes(object):

    def __init__(self, infofilename, datafilename):
        self.info = InfoReader(infofilename)
        self.data = DataReader(datafilename)
        self.digested = {}
        self.name_to_id = {}

    def read(self):
        for _ in self.info:
            pass
        for _ in self.data:
            pass
        for id_, d in self.info.data.items():
            # http://www.census.gov/geo/ZCTA/zctafaq.html#Q10
            if d['NAME'].endswith('HH'):  # 'HH' := hydrographic feature
                del self.info.data[id_]
                del self.data.polys[id_]
            elif d['NAME'].endswith('XX'):
                # 'XX' := rural area that was too sparsely populated.
                # There are no real nzipcodes ending in 0
                d['NAME'] = d['NAME'].replace('X', '0')
                d['FIPS CODE(S)'] = d['FIPS CODE(S)'].replace('X', '0')

    def digest(self):
        names = set(x['NAME'] for x in self.info.data.values())
        for id_, d in self.info.data.items():
            try:
                self.name_to_id[d['NAME']].append(id_)
            except KeyError:
                self.name_to_id[d['NAME']] = [id_]
        for name in names:
            self.digested[name] = ps = []
            for id_ in self.name_to_id[name]:
                ps.append(self.data.polys[id_])

    def save_to_file(self, filename):
        output = []
        print len(self.digested)
        for name, shapes in self.digested.items():
            output.extend([name,
                           ':',
                           repr(shapes),
                           '\n'])
        s = ''.join(output).replace('[', '(').replace(']', ')')
        open(filename, 'w').write(s)

def dat_to_fov(info_file, data_file, outfile):
    """
    Convert the two files into a colon-delimited file.

    The output format has one zip code per line, and each line
    is formatted as follows:

        zipcode:[shape1, shape2, ... shape_n]

    where each shape is of the form

        (poly1, poly2, ... poly_n)

    where the first polygon is part of the shape and the remaining
    polygon cut out holes from it. Each polygon is of the form

        ((x1, y1), (x2, y2), ... (x_n, y_n))
    """
    z = ZipCodes(info_file, data_file)
    z.read()
    z.digest()
    z.save_to_file(outfile)
    print "Saved to %s" % outfile

INFO_FILE = "zt42_d00a.dat"
DATA_FILE = "zt42_d00.dat"
POLY_FILE = 'zipcode-polys.txt'

if __name__ == "__main__":
    dat_to_fov(INFO_FILE, DATA_FILE, POLY_FILE)
