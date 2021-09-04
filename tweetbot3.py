import sys, twitter, pywikibot, requests
from search import Get_Results
import secrets
import tsd_utils.utils2


class TweetBot:
    def __init__(self, search):
        self.site = pywikibot.Site()
        self.api = api = twitter.Api(consumer_key=secrets.consumer_key,
                                     consumer_secret=secrets.consumer_secret,
                                     access_token_key=secrets.oauth_access_token,
                                     access_token_secret=secrets.oauth_access_token_secret)
        self.archive_urls = False
        self.results = Get_Results(search).process()

    def run(self):
        for article in self.results:
            page = pywikibot.Page(self.site, article)
            print("Working with " + article)
            text = page.text
            try:
                tsd_utils.utils2.save_edit(self.site, self.api, page, self.archive_urls, text)
            except ValueError as err:
                print(err)


def main():
    bot = TweetBot('insource:"\<ref\>https?://twitter\.com/"')
    bot.run()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        sys.exit(0)
