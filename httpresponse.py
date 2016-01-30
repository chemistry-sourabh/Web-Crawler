#!/usr/bin/python

class HTTPresponse():

    def __init__(self):
        # the variables are self explanatory
        self.version = ""
        self.status = 0
        self.status_message = ""
        self.csrf = ""
        self.session = ""
        self.location = ""
        self.content_length = 0
        self.max_connections = 0
        self.content_encoding = ""
        self.transfer_encoding = ""
        self.content = ""

    def ishex(self,str):
        try:
            int(str,16)
            return True
        except:
            return False

    # parse the response
    def parse(self,response):
        # split into lines
        lines = response.split('\r\n')

        # parse status line
        status_line = lines[0]
        status_parts = status_line.split(" ")
        self.version = status_parts[0][-3:]
        self.status = int(status_parts[1])
        self.status_message = status_parts[2]

        # parse cookies if present, but only csrf and session
        # assuming the cookies returned are csrf and session only
        cookies = filter(lambda line: line.startswith("Set-Cookie"),lines)

        csrfcookie = ""
        sessioncookie = ""

        for cookie in cookies:
            if "csrftoken" in cookie:
                csrfcookie = cookie
            elif "sessionid" in cookie:
                sessioncookie = cookie

            if csrfcookie != "":
                self.csrf = csrfcookie[csrfcookie.index('=')+1:csrfcookie.index(';')]
            if sessioncookie != "":
                self.session = sessioncookie[sessioncookie.index('=')+1:sessioncookie.index(';')]

        # to detect start of content
        blank_line = False

        for line in lines:

            if line == '':
                blank_line = True
                continue
            # parse headers for required headers
            if not blank_line:
                if line.startswith("Transfer-Encoding"):
                    self.transfer_encoding = line.split(' ')[1]

                elif line.startswith("Keep-Alive"):
                    self.max_connections = int(line.split(' ')[2].split('=')[1])

                elif line.startswith("Content-Encoding"):
                    self.content_encoding = line.split(' ')[1]

                elif line.startswith("Location"):
                    self.location = line.split(' ')[1]

                elif line.startswith("Content-Length"):
                    self.content_length = int(line.split(' ')[1])

            # get content and join chunked content
            else:
                if self.transfer_encoding == 'chunked':
                        if line != '' and not self.ishex(line.strip()):
                            self.content = self.content + line
                else:
                    self.content = self.content + line