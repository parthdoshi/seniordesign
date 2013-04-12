
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
        self.multiple = False
        self.active = False

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
        return 0

    def start_poly(self, id_):
        if id_ == "-99999":
            self.multiple = True
            self.polys[self.current_id] = [self.polys[self.current_id]]
        else:
            self.current_id = int(id_)
            self.multiple = False

    def end_poly(self):
        if self.multiple:
            self.polys[self.current_id].append(self.current_poly)
        else:
            self.polys[self.current_id] = self.current_poly
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

    def read(self):
        for _ in self.info:
            pass
        for _ in self.data:
            pass
        print set(self.info.data).symmetric_difference(self.data.polys)

    def save_to_file(self, filename):
        ids = self.info.data.keys()
        output = []
        for id_ in ids:
            output.append(self.info.data[id_]['NAME'] + ':')
            output.append(repr(self.data.polys[id_]))
            output.append('\n')
        open(filename, 'w').write(''.join(output))

INFO_FILE = "zt42_d00a.dat"
DATA_FILE = "zt42_d00.dat"

def main():
    z = ZipCodes(INFO_FILE, DATA_FILE)
    z.read()
    z.save_to_file('zipcode-polys')

if __name__ == "__main__":
    main()
