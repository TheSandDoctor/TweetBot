#!/usr/bin/python3

"""
    search.py

    MediaWiki API Demos
    Demo of `Search` module: Search for a text or title

    MIT License
"""

import requests

S = requests.Session()

URL = "https://en.wikipedia.org/w/api.php"

SEARCHPAGE = 'insource:"\<ref\>https?://twitter\.com/"'

PARAMS = {
    "action": "query",
    "format": "json",
    "list": "search",
    "srsearch": SEARCHPAGE,
    "srlimit":500,
    "sroffset": 0
}

R = S.get(url=URL, params=PARAMS)
DATA = R.json()

#if DATA['query']['search'][0]['title'] == SEARCHPAGE:
#    print("Your search page '" + SEARCHPAGE + "' exists on English Wikipedia")
print(DATA['query']['searchinfo']['totalhits'])
