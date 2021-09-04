#!/usr/bin/python3
import requests


class Get_Results:
    def __init__(self, search: str):
        self.search = search
        self.session = requests.Session()
        self.url = "https://en.wikipedia.org/w/api.php"
        self.result = []

    def set_search(self, search: str):
        if type(search) is not str:
            raise TypeError("Must be str")
        self.search = search

    def find(self, limit=500, offset=0):
        params = {
            "action": "query",
            "format": "json",
            "list": "search",
            "srsearch": self.search,
            "srlimit": limit,
            "sroffset": offset
        }
        req = self.session.get(url=self.url, params=params)
        data = req.json()
        total = data['query']['searchinfo']['totalhits']
        for i in data['query']['search']:
            self.result.append(i['title'])
        if (total > offset) and (offset + limit) < total:
            print(offset + limit)
            return self.find(offset=offset + limit)

    def process(self):
        self.find()
        return list(dict.fromkeys(self.result))