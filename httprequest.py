#!/usr/bin/python


class HTTPrequest():

    def __init__(self):
        # self explanatory
        self.type = ""
        self.path = ""
        self.version = ""
        self.host = ""
        self.connection = ""
        self.encoding = ""
        self.useragent = "WebCrawler/1.0"
        self.cookies = {}
        self.content_type = ""
        self.content = ""

    # called when object requires to be converted to string
    # the request is assembled from the variables and is returned
    def __str__(self):
        request = self.type + " "+self.path+" HTTP/"+self.version+"\r\n"
        request += "Host: "+self.host+"\r\n"
        if self.cookies.__len__() >= 1:
            request = request + "Cookie: "
            if self.cookies.has_key('csrf'):
                request = request + "csrftoken="+self.cookies['csrf']
            if self.cookies.has_key('sessionid'):
                request = request + "; sessionid="+self.cookies['sessionid']
            request += "\r\n"
        request += "User-Agent: " + self.useragent + "\r\n"
        if not self.encoding == "":
            request += "Accept-Encoding: "+self.encoding+"\r\n"
        if not self.connection == "":
            request += "Connection: "+self.connection+"\r\n"
        if not self.content_type == "":
            request += "Content-Type: " + self.content_type + "\r\n"
        if not self.content == "":
            request += "Content-Length: " + str(self.content.__len__()) + "\r\n"
        request += "\r\n"  # blank line before content
        request += self.content
        return request
