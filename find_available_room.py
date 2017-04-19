#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

import subprocess
import getpass
from string import Template
import xml.etree.ElementTree as ET
import csv, codecs
import argparse
import datetime

now = datetime.datetime.now().replace(microsecond=0)
starttime_default = now.isoformat()
end_time_default = None

parser = argparse.ArgumentParser()
parser.add_argument("-url","--url", help="url for exhange server, e.g. 'https://mail.domain.com/ews/exchange.asmx'.",required=True)
parser.add_argument("-u","--user", help="user name for exchange/outlook",required=True)
parser.add_argument("-p","--password", help="password for exchange/outlook", required=True)
parser.add_argument("-start","--starttime", help="Starttime e.g. 2014-07-02T11:00:00 (default = now)", default=starttime_default)
parser.add_argument("-end","--endtime", help="Endtime e.g. 2014-07-02T12:00:00 (default = now+1h)", default=end_time_default)
#parser.add_argument("-n","--now", help="Will set starttime to now and endtime to now+1h", action="store_true")
parser.add_argument("-f","--file", help="csv filename with rooms to check (default=favorites.csv). Format: Name,email",default="favorites.csv")

args=parser.parse_args()

url = args.url

reader = csv.reader(codecs.open(args.file, 'r', encoding='utf-8')) 

start_time = args.starttime
if not args.endtime:
	start = datetime.datetime.strptime( start_time, "%Y-%m-%dT%H:%M:%S" )
	end_time = (start + datetime.timedelta(hours=1)).isoformat()
else:
	end_time = args.endtime

user = args.user
password = args.password

print "Searching for a room from " + start_time + " to " + end_time + ":"
print "{0:10s} {1:25s} {2:40s} {3:10s} {4:10s} {5:10s} {6:50s}".format("Status", "Room", "Email", "Level", "Zone", "Seats", "Description")

xml_template = open("getavailibility_template.xml", "r").read()
xml = Template(xml_template)
for room in reader:
	data = unicode(xml.substitute(email=room[1],starttime=start_time,endtime=end_time))
	header = "\"content-type: text/xml;charset=utf-8\""
	command = "curl --silent --header " + header +" --data '" + data + "' --ntlm -u "+ user+":"+password+" "+ url
	response = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True).communicate()[0]
	tree = ET.fromstring(response)

	status = "Free"
	# arrgh, namespaces!!
	elems=tree.findall(".//{http://schemas.microsoft.com/exchange/services/2006/types}BusyType")
	for elem in elems:
		status=elem.text
	print "{0:10s} {1:25s} {2:40s} {3:10s} {4:10s} {5:10s} {6:50s}".format(status, room[0], room[1], room[2], room[3], room[4], room[5] )