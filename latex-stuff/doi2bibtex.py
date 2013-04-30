
"""
This script accepts a DOI as an input and uses the Crossref API to
retrieve citation info in bibtex format. It can also append to an
existing bib file.

See http://tex.stackexchange.com/a/45559/6619 for the inspiration

Also see
http://www.crossref.org/CrossTech/2011/11/turning_dois_into_formatted_ci.html
"""

import argparse
import re
import urllib2


def get_bib(doi):
    """Retrieve the bib data as a single string for a DOI."""
    req = urllib2.Request('http://dx.doi.org/')
    req.add_header('Accept', 'text/bibliography; style=bibtex')
    resp = urllib2.urlopen(req)
    if resp.getcode() != 200:
        raise Exception("HTTP Error!")
    return resp.read()
    
def format_bib(text):
    """Convert a one-line bib string to a multi-line string."""
    tokens = re.split('([,={}]|\s)\s*', text)
    stack = [[]]
    for token in tokens:
        if token == '{':
            stack.append(['{'])
        elif token == '}':
            if len(stack) < 1:
                raise Exception("Parse Error! Unmatched '}'")
            stack[-1].append('}')
            s = ''.join(stack.pop(-1))
            stack[-1].append(s)
            if len(stack) == 1:
                return s
        elif token == ',' and len(stack) == 2:
            stack[-1].append(',\n  ')
        elif token.strip() or len(stack) > 2:
            stack[-1].append(token)
    raise Exception("Parse Error! Unmatched '{'")
    
def write_bib(filelike, bibtext):
    """Write an entry to an open bibfile."""
    filelike.write('\n\n')
    filelike.write(bibtext)

def parse_args():
    parser = argparse.ArgumentParser('')
    help = "The DOI of the resource to add"
    parser.add_argument("doi", help=help)
    help="The name of the bibfile to save record to"
    parser.add_argument("bibfile", help=help, nargs='?',
                        type=argparse.FileType('at'))
    args = parser.parse_args()
    if args.bibfile is None:
        import sys
        args.bibfile = sys.stdout
    return args.doi, args.bibfile

if __name__ == "__main__":
    doi, out = parse_args()
    raw = get_bib(doi)
    bib = format_bib(raw)
    print bib
    write_bib(raw, out)
    
