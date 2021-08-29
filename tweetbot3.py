import sys, twitter, pywikibot
from searching import Get_Results
import secrets
import tsd_utils.utils2

def main():
    site = pywikibot.Site()

    api = twitter.Api(consumer_key=secrets.consumer_key,
                      consumer_secret=secrets.consumer_secret,
                      access_token_key=secrets.oauth_access_token,
                      access_token_secret=secrets.oauth_access_token_secret)

    archive_urls = False
    search = Get_Results('insource:"\<ref\>https?://twitter\.com/"')
    results = search.process()
    for article in results:
        page = pywikibot.Page(site, article)
        print("Working with " + article)
        text = page.text
        try:
            tsd_utils.utils2.save_edit(site, api, page, archive_urls, text)
        except ValueError as err:
            print(err)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        sys.exit(0)
