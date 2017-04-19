#!/usr/bin/env python2.7

from flask import Flask, request, jsonify
import json, datetime
import sys, os
from string import Template
import xml.etree.ElementTree as ET
import subprocess
import requests
import sys
reload(sys)
sys.setdefaultencoding("utf-8")
import getpass
import csv, codecs
import argparse
import datetime
from requests_ntlm import HttpNtlmAuth
from threading import Thread
from Queue import Queue

app = Flask(__name__,static_folder='static')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        room_name = request.form["room_name"]
        room_email = request.form["room_email"]
        user_email = request.form["user_email"]

        now = datetime.datetime.now().replace(microsecond=0)
        start_time = now.isoformat()
        end_time = (now + datetime.timedelta(hours=1)).isoformat()
        book_room(room_name, room_email, user_email, user_email, start_time, end_time)
        return "Room "+str(room_name)+" booked for "+user_email+" from "+str(start_time)+" to "+str(end_time)
    else:
        return "Error should be a POST"

@app.route('/book', methods=['GET', 'POST'])
def book():
    if request.method == 'POST':
        j = request.get_json(force=True)
        sys.stderr.write("Type: "+str(type(j))+"\n")
        sys.stderr.write("j: "+str(j)+"\n")
        sys.stderr.write("user_name: "+str(j["data"]['user_name'])+"\n")
        sys.stderr.write("user_email: "+str(j["data"]['user_email'])+"\n")
        sys.stderr.write("start_time: "+str(j["data"]['starttime'])+"\n")
        sys.stderr.write("end_time: "+str(j["data"]['endtime'])+"\n")
        sys.stderr.write("room_name: "+str(j["data"]['room_name'])+"\n")

        xml_template = open("resolvenames_template.xml", "r").read()
        xml = Template(xml_template)
        data = unicode(xml.substitute(name=str(j["data"]["room_name"])))
        header = "\"content-type: text/xml;charset=utf-8\""
        command = "curl --silent --header " + header +" --data '" + data + "' --ntlm "+ "-u "+ user+":"+password+" "+ url
        #print "command: "+str(command)
        response = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True).communicate()[0]
        print "response: "+str(response)
        tree = ET.fromstring(response.encode('utf-8'))

        elems=tree.findall(".//{http://schemas.microsoft.com/exchange/services/2006/types}Resolution")
        for elem in elems:
            room_email = elem.findall(".//{http://schemas.microsoft.com/exchange/services/2006/types}EmailAddress")[0].text
            room_name = elem.findall(".//{http://schemas.microsoft.com/exchange/services/2006/types}DisplayName")[0].text

        sys.stderr.write("room_email: "+str(room_email)+"\n")
        if room_email=="":
            return "Sorry, "+str(j["data"]["room_name"])+" does not exists !"
        else:
            book_room(str(j["data"]["room_name"]), room_email, str(j["data"]["user_name"]), str(j["data"]["user_email"]), str(j["data"]["starttime"]), str(j["data"]["endtime"]))
            return "Room "+str(j["data"]["room_name"])+" booked for "+str(j["data"]["user_name"]+" from "+str(j["data"]["starttime"])+" to "+str(j["data"]["endtime"]))
    else:
        return "Error should be a POST"

@app.route('/available', methods=['GET'])
def available():
    reader = csv.reader(codecs.open(file, 'r', encoding='utf-8'))
    now = datetime.datetime.now().replace(microsecond=0)
    start_time = now.isoformat()
    end_time = (now + datetime.timedelta(hours=1)).isoformat()
    print "Searching for a room from " + start_time + " to " + end_time + ":"
    #print "{0:10s} {1:25s} {2:40s} {3:10s} {4:10s} {5:10s} {6:50s}".format("Status", "Room", "Email", "Level", "Zone", "Seats", "Description")
    
    file2 = open("getavailibility_template.xml", "r")
    xml_template = file2.read()
    xml = Template(xml_template)
    data_json = []
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
    	
    	#print "{0:10s} {1:25s} {2:40s} {3:10s} {4:10s} {5:10s} {6:50s}".format(status, room[0], room[1], room[2], room[3], room[4], room[5] )
    	row = [status, room[0], room[1], room[2], room[3], room[4], room[5]]
    	data_json.append(row)
    file2.close()
    data_json_response = ["List of rooms status <br> in Dimension Data <br> from " + start_time +" <br> to " + end_time]
    data_json_response.append(data_json)

    #print data_json_response
    resp = jsonify(data_json_response)
    resp.status_code = 200
    return resp

@app.route('/available2', methods=['GET'])
def available2():
    rooms={}
    now = datetime.datetime.now().replace(microsecond=0)
    start_time = now.isoformat()
    end_time = (now + datetime.timedelta(hours=1)).isoformat()
    reader = csv.reader(codecs.open(file, 'r', encoding='utf-8')) 
    for row in reader: 
        rooms[unicode(row[1])]=unicode(row[0])
    update_scheduler()
    xml_template = open("getavailibility_template.xml", "r").read()
    xml = Template(xml_template)
    result=list()

    for i in range(concurrent):
        t = Thread(target=doWork)
        t.daemon = True
        t.start()
    sys.stderr.write(str(now.isoformat())+": End of init of Thread start\n")
    try:
        for room in rooms:
            q.put(unicode(xml.substitute(email=room,starttime=start_time,endtime=end_time)))
        sys.stderr.write(str(now.isoformat())+": End of send data to process to Thread\n")
        q.join()
        sys.stderr.write(str(now.isoformat())+": End of join Thread\n")
    except KeyboardInterrupt:
        sys.exit(1)
        
    resp = json.dumps(((("List of rooms status","in Dimension Data","from " + start_time,"to " + end_time),sorted(result, key=lambda tup: tup[1]))))
    return resp

def book_room(room_name, room_email, user_name, user_email, start_time, end_time):
    xml_template = open("book_room.xml", "r").read()
    xml = Template(xml_template)
    data = unicode(xml.substitute(starttime=start_time,endtime=end_time,user=user_name,user_email=user_email,room=room_name,room_email=room_email))
    return send_request(data)   
 

def doWork():
    while True:
        data = q.get()
        response = send_request(data)
        doSomethingWithResult(response)
        q.task_done()
        
def send_request(data):
    try:
        headers = {}
        #headers["Content-type"] = "text/xml; charset=utf-8"
        #response=requests.post(url,headers = headers, data= data, auth=HttpNtlmAuth(user,password))
        header = "\"content-type: text/xml;charset=utf-8\""
        #response=requests.post(url,headers = headers, data= data, auth= HttpNtlmAuth(user,password))
        command = "curl --silent --header " + header +" --data '" + data + "' --ntlm -u "+ user+":"+password+" "+ url
    	response = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True).communicate()[0]
        return response
    except:
        print "ERROR"
        return None

def doSomethingWithResult(response):
    if response is None:
        return "KO"
    else:
        tree = ET.fromstring(response.text)
        print response
        status = "Free"
        # arrgh, namespaces!!
        elems=tree.findall(".//{http://schemas.microsoft.com/exchange/services/2006/types}BusyType")
        for elem in elems:
            status=elem.text

        tree2=ET.fromstring(response.request.body)
        elems=tree2.findall(".//{http://schemas.microsoft.com/exchange/services/2006/types}Address")
        for e in elems:
            room=e.text

        sys.stderr.write(str(now.isoformat())+": Status for room: "+str(room)+" => "+status+"\n")
        #result.append((status, rooms[room], room))


if __name__ == '__main__':
    now = datetime.datetime.now().replace(microsecond=0)
    starttime_default = now.isoformat()
    end_time_default = None
    from argparse import ArgumentParser
    parser = ArgumentParser("Room Finder Book Room Service")
    parser.add_argument("-url","--url", help="url for exchange server, e.g. 'https://mail.domain.com/ews/exchange.asmx'.")
    parser.add_argument("-u","--user", help="user for exchange server, e.g. 'toto@toto.com'.")
    parser.add_argument("-p","--password", help="password for exchange server.")
    parser.add_argument("-start","--starttime", help="Starttime e.g. 2014-07-02T11:00:00 (default = now)", default=starttime_default)
    parser.add_argument("-end","--endtime", help="Endtime e.g. 2014-07-02T12:00:00 (default = now+1h)", default=end_time_default)
    #parser.add_argument("-n","--now", help="Will set starttime to now and endtime to now+1h", action="store_true")
    parser.add_argument("-f","--file", help="csv filename with rooms to check (default=favorites.csv). Format: Name,email",default="favorites.csv")
    args = parser.parse_args()

    url = args.url

    if (url == None):
        url = os.getenv("roomfinder_exchange_server")
        # print "Exchange URL: " + str(url)
        if (url == None):
            get_exchange_server = raw_input("What is the Exchange server URL? ")
            # print "Input URL: " + str(get_exchange_server)
            url = get_exchange_server

    # sys.stderr.write("Exchange URL: " + url + "\n")

    user = args.user

    if (user == None):
        user = os.getenv("roomfinder_exchange_user")
        # print "Exchange user: " + str(user)
        if (user == None):
            get_exchange_user = raw_input("What is the Exchange user? ")
            # print "Input Exchange user: " + str(get_exchange_user)
            user = get_exchange_user

    # sys.stderr.write("Exchange user: " + user + "\n")

    password = args.password

    if (password == None):
        password = os.getenv("roomfinder_exchange_password")
        # print "Exchange password: " + str(password)
        if (password == None):
            get_exchange_password = raw_input("What is the Exchange server password? ")
            # print "Input Exchange password: " + str(get_exchange_password)
            password = get_exchange_password

    # sys.stderr.write("Exchange password: " + password + "\n")

    start_time = args.starttime
    if not args.endtime:
    	start = datetime.datetime.strptime( start_time, "%Y-%m-%dT%H:%M:%S" )
    	end_time = (start + datetime.timedelta(hours=1)).isoformat()
    else:
    	end_time = args.endtime
    
    file = args.file
    
    concurrent=20
    q = Queue(concurrent * 2)

    try:
    	app.run(debug=True, host='0.0.0.0', port=int("8081"))
    except:
    	try:
    		app.run(debug=True, host='0.0.0.0', port=int("8081"))
    	except:
    		print "Web server error"
    		

