from HTMLParser import HTMLParser
from tag import Tag


class BetterHTMLParser(HTMLParser):


    def __init__(self):
        HTMLParser.__init__(self)
        self.tags = []
        self.nftags = []


    def handle_starttag(self, tag, attrs):
        self.nftags.append(Tag(tag,attrs))

    def handle_endtag(self, tag):
        self.tags.append(self.nftags.pop(-1))

    def handle_data(self, data):
        if not self.nftags.__len__() == 0:
            self.nftags[-1].data = data
