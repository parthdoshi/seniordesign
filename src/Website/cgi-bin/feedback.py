#!/usr/local/bin/python
import cgi
# import csv
import cgitb
from string import Template
# import time
# import urllib2
# import json
cgitb.enable()

def main():
    form = cgi.FieldStorage() # parse query

    name = ""
    if form.has_key("name") and form["name"].value != "":
        name = form["name"].value
    email = ""
    if form.has_key("email") and form["email"].value != "":
        email = form["email"].value
    comment = ""
    if form.has_key("comment") and form["comment"].value != "":
        comment = form["comment"].value

    st = name + " " + email + " " + comment + "\n"
    f = open("comments.txt", 'a')
    f.write(st)
    f.close()

    TEMPLATE = Template(open('template.html').read())
    html = TEMPLATE.substitute(title="Thank You", content='<h2>Thank you for taking the time to give us feedback!</h2>')
    print "Content-type: text/html\n"
    # print "<h1> Hello </h1>"
    print html

main()