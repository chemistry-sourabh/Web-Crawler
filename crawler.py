#!/usr/bin/python

from bs4 import BeautifulSoup
from httprequest import HTTPrequest
from httpresponse import HTTPresponse
from urlparse import *
import socket
from threading import Thread, Lock
import threading
import argparse

#parser for parsing commandline arguments of username and password
parser = argparse.ArgumentParser(description='crawls fakebook')

# add username and password arguments
parser.add_argument("username", help="username of fakebook")
parser.add_argument("password", help="password of fakebook")

#parse arguments
args = parser.parse_args()

#assign arguments to variables
username = args.username
password = args.password

# mutex lock for thread synchronization
mutex = Lock()
# the queue which stores the links to crawl
link_queue = []
# the queue which stores the visisted links to prevent loops
visited = []
# the host name to compare so that the crawler doesnt go follow links which are outside fakebook
default_netloc = ""
# host to connect to
host = "fring.ccs.neu.edu"
# fakebook login link
login_link = "http://fring.ccs.neu.edu/accounts/login/?next=/fakebook/"
# list which stores secret flags
secret_flags = []

# function to send HTTP request to host
def sendRequest(host,request):

    # create socket and connect to HTTP port of host
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((host,80))

    # send request
    # request is a HTTPrequest object which is implemented by us, the string of the object gives the request to be sent
    s.send(str(request))

    # get response
    # loop until blank string is returned
    response = ""
    while True:
        received = s.recv(1000)
        response = response + received
        if received == "":
            break

    s.close() # close socket

    # create a HTTPresponse object and parse the required response
    httpresponse = HTTPresponse()
    httpresponse.parse(response)
    return httpresponse

# function to get csrf token from page
def getCSRF(login_link):

    # parse link using urlparse
    parsedLink = urlparse(login_link)

    # create request using HTTPrequest object
    request = HTTPrequest()

    # set parameters of request
    request.type = "GET"
    request.host = parsedLink.netloc
    request.path = parsedLink.path
    request.version = "1.1"
    request.connection = "close"

    # send request and get response
    httpresponse = sendRequest(parsedLink.netloc,request)
    return httpresponse.csrf # return csrf token


# function to login to fakebook
def login_to_fakebook(login_link,username,password,csrf):

    # parse login link
    parsedLink = urlparse(login_link)

    # set parameters for HTTPrequest object
    loginrequest = HTTPrequest()
    loginrequest.type = "POST"
    loginrequest.version = "1.1"
    loginrequest.host = parsedLink.netloc
    loginrequest.path = parsedLink.path
    loginrequest.connection = "Keep-Alive"
    loginrequest.cookies['csrf'] = csrf # setting the csrf token from previous request
    loginrequest.content_type = "application/x-www-form-urlencoded"
    loginrequest.content = "username="+username+"&password="+password+"&csrfmiddlewaretoken="+csrf # the content

    # send request and return response
    loginresponse = sendRequest(parsedLink.netloc,loginrequest)
    return loginresponse

# function to be executed by the threads of the crawler
def crawler_thread(csrf,session_id):

    # to keep track of the links sent by the thread
    sent_links = []


    # the function to be executed by the sending thread of the crawler thread
    # this simply sends requests for the links in the link_queue to implement pipelining
    def sendRequests(csrf,session,s):

        # repeat until link_queue is not empty
        while link_queue.__len__() > 0:

            # acquire mutex to prevent sync issues
            mutex.acquire()

            # pop link from queue
            # can crash as queue could be empty due to other threads
            try:
                link = link_queue.pop(0)
            except IndexError:
                mutex.release() # release mutex and break
                break

            # if the popped link is not a visited link then send request to it
            if link not in visited:

                # make request object for it
                parsed = urlparse(link)
                linkrequest = HTTPrequest()
                linkrequest.type = "GET"
                linkrequest.version = "1.1"
                linkrequest.host = parsed.netloc
                linkrequest.path = parsed.path
                linkrequest.cookies['csrf'] = csrf # send csrf token
                linkrequest.cookies['sessionid'] = session # send session id
                linkrequest.connection = "Keep-Alive" # for pipelining

               # send the request
                try:
                    s.send(str(linkrequest))
                    # if no error add link to sent links
                    sent_links.append(link)

                except socket.error:
                    # if error occurs due to various reasons then insert link at start of queue
                    link_queue.insert(0,link)
                    mutex.release() # release mutex and break
                    #s.close()
                    break
            mutex.release() # release mutex after successful transmission so that other threads can transmit

    # function which processes responses
    def process_response(response):
        # if it is redirect then add the link to the visisted and insert the new link at start of queue
        if 300 <= response.status < 400:
            visited.append(sent_links.pop(0))
            link_queue.insert(0,response.location)
        # if it is internal error then insert the same link again at start of queue
        elif 500 <= response.status < 600:
            link = sent_links.pop(0)
            link_queue.insert(0,link)
        # if it is normal response then parse it and search for valid links and secret flags
        elif response.status == 200 and response.status_message == 'OK':
            # add to visited links
            visited.append(sent_links.pop(0))

            # parse the content of response
            soup = BeautifulSoup(response.content,"html.parser")

            # extract a and h2 tags with secret flag class
            a_tags = soup.find_all('a')
            h2_tags = soup.find_all('h2',{'class':'secret_flag'})

            # add the flag in h2 tag if it is a new flag
            for h2_tag in h2_tags:
                if h2_tag.contents[0].split(" ")[1] not in secret_flags:
                    secret_flags.append(h2_tag.contents[0].split(" ")[1])

            # loop through the a tags and add links if it is not in visited and a http link in fakebook
            for a_tag in a_tags:
                if urljoin(default_netloc,a_tag['href']) not in visited:
                    parsed = urlparse(a_tag['href'])
                    if (parsed.netloc == '' or parsed.netloc == urlparse(default_netloc).netloc) and \
                        (parsed.scheme == 'http' or parsed.scheme == ''):
                        if parsed.netloc == '':
                            link_queue.append(urljoin(default_netloc,a_tag['href']))
                        else:
                            link_queue.append(a_tag['href'])

    # function to execute by receiving thread
    def receive_responses(s):

        # string which stores response
        response = ""

        # loop until blank string is received
        while True:
            try:
                received = s.recv(1000) # receive response
            except socket.error:
                break # break if some error happens
            response = response + received # append response
            mutex.acquire() # acquire mutex
            # break the response string into individual responses if 2 or more are present and process them
            while response.count("HTTP/1.1") >= 2:
                # response splitting code
                httpresponse = HTTPresponse()
                second_http_index = response.find("HTTP/1.1","HTTP/1.1".__len__())
                one_response = response[0:second_http_index]
                # process response
                if not one_response == "":
                    httpresponse.parse(one_response)
                    process_response(httpresponse)
                # update response to break from loop
                response = response[second_http_index:]
            mutex.release() # release mutex so that other threads can work

            # break if blank string is received
            if received == "":
                break

        # acquire mutex
        mutex.acquire()
        # do the same stuff like above
        while response.count("HTTP/1.1") >= 2:
                httpresponse = HTTPresponse()
                second_http_index = response.find("HTTP/1.1","HTTP/1.1".__len__())
                one_response = response[0:second_http_index]
                if not one_response == "":
                    httpresponse.parse(one_response)

                    process_response(httpresponse)
                response = response[second_http_index:]

        # this is to process the final response left in the string response
        if not response == "":
            httpresponse = HTTPresponse()
            httpresponse.parse(response)
            process_response(httpresponse)

        # incase a socket error happens there might be some links whose responses were not processed
        # add these links back to the queue at the start so that they are not missed
        if sent_links.__len__() > 0:
            for sent_link in sent_links:
                link_queue.insert(0,sent_link)
        s.close() # close socket to signal the sending thread to stop and also since it is bad to leave a socket open
        mutex.release() # release the mutex

    # this is the logic which happens in crawler thread
    # create a socket unique to the thread which connects to HTTP port of fakebook
    thread_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    thread_socket.connect((host,80))

    # this is for pipelining
    # start sending thread to send requests
    sending = Thread(target=sendRequests,args=(csrf,session_id,thread_socket))
    sending.setDaemon(True)
    sending.setName("Sending Thread for "+threading.current_thread.__name__)
    sending.start()

    # start receiving thread to receive and process responses
    receiving = Thread(target=receive_responses, args=(thread_socket,))
    receiving.setDaemon(True)
    receiving.setName("Receiving Thread for "+threading.current_thread.__name__)
    receiving.start()


# the main logic starts here
# get csrf token from login page
import  time
time1 = time.time()
csrf = getCSRF(login_link)
 # login to fakebook to get session id and max connections
response = login_to_fakebook(login_link,username,password,csrf)
session_id = response.session
max_connections = response.max_connections


# add the redirection link to start crawling
if response.location != "":
    link_queue.append(response.location)

# store the link to check if the future links are part of fakebook
default_netloc = response.location

while  threading.enumerate().__len__() > 1 or link_queue.__len__() != 0:

    # if the number of active threads are less than max_connections times 3 as each crawler thread is 3 threads
    # (crawler,sending and receiving)
    # didnt multiply since dont know whether CCIS machines could handle 300 threads!!
    # also checking if link queue has links then create a crawler thread to crawl the available links
    if threading.enumerate().__len__() <= max_connections and link_queue.__len__() > 0:
        t = Thread(target=crawler_thread,args=(csrf,session_id))
        t.setDaemon(True)
        t.start()

    # if 5 flags are found break
    if secret_flags.__len__() == 5:
        break

# print secret flags
for secret_flag in secret_flags:
    print secret_flag
time2 = time.time()

print time2 - time1