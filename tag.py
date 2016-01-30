
class Tag:

    def __init__(self,name, attrs):
        self.name = name
        self.attrs = {}
        for attr in attrs:
            self.attrs[attr[0]] = attr[1]
        self.data = ""

    def __str__(self):
        return "<"+ self.name + str(self.attrs) + ">"+self.data+"</"+self.name+">"
