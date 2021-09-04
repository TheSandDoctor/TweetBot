#!/usr/bin/python3
import requests

class Get_Results:
    def __init__(self, search:str):
        self.search = search
        self.session = requests.Session()
        self.url = "https://en.wikipedia.org/w/api.php"
        self.result = []

    def set_search(search:str):
        if type(search) is not str:
            raise TypeError("Must be str")
        self.search = search

    def find(self, limit=500, offset=0):
        PARAMS = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": self.search,
            "srlimit":limit,
            "sroffset": offset
        }
        R = self.session.get(url=self.url, params=PARAMS)
        DATA = R.json()
        total = DATA['query']['searchinfo']['totalhits']
        for i in DATA['query']['search']:
            self.result.append(i['title'])
        if (total > offset) and (offset + limit) < total:
            print(offset+limit)
            return self.find(offset=offset + limit)
    def process(self):
        self.find()
        return list(dict.fromkeys(self.result))


if __name__ == "__main__":
    search = Get_Results('insource:"\<ref\>https?://twitter\.com/"')
    result = search.process()
    print(result[0])
    print(result[-1])
