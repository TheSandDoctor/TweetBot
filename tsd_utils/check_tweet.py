# coding: utf-8
import twitter, secrets, re, textwrap, waybackpy
from datetime import datetime
from twitter.error import TwitterError
from dateutil.parser import *


class CheckTweet:
    def __init__(self, tweet_id):
        self.id = tweet_id
        self.api = twitter.Api(consumer_key=secrets.consumer_key,
                               consumer_secret=secrets.consumer_secret,
                               access_token_key=secrets.oauth_access_token,
                               access_token_secret=secrets.oauth_access_token_secret)
        self.tweet = self.check_id()

    def check_id(self):
        try:
            return self.api.GetStatus(self.id)
        except TwitterError:
            return None

    def clean_tweet(self):
        if not self.tweet:
            raise ValueError("No valid tweet")
        url_reg = r'((?:\s)*https?:\/\/)?(?:www\.)?(?:\s)*?t\.co\/([a-zA-Z0-9])*'
        sec_pattern = r'/\r|\n/'
        tweet_text = re.sub(url_reg, '', self.tweet.text, re.UNICODE)
        tweet_text = re.sub(sec_pattern, ' ', tweet_text, re.UNICODE)
        # print("After edit" + tweet_text)
        # tweet_text = textwrap.shorten(tweet_text, width=40, placeholder="...")
        # self.truncateUTF8length(tweet_text, 15)
        tweet_obj = "{{cite tweet|number=" + str(
            self.id) + "|user=" + self.tweet.user.screen_name + "|title=" + tweet_text + "<!-- full text of tweet " \
                                                                                         "that Twitter returned to " \
                                                                                         "the bot (" \
                                                                                         "excluding links) added by " \
                                                                                         "TweetCiteBot. This may be " \
                                                                                         "better truncated or may " \
                                                                                         "need expanding (TW limits " \
                                                                                         "responses to 140 " \
                                                                                         "characters) or case " \
                                                                                         "changes. --> "
        return tweet_obj

    def gen_date(self, use_mdy):
        if not self.tweet:
            raise ValueError("No valid tweet")
        date_format = '%-d %B %Y'
        if use_mdy:
            date_format = '%B %-d, %Y'
        return "|date=" + parse(self.tweet.created_at).strftime(date_format)

    def is_wayback_live(self, url):
        wb = waybackpy.Url(str(url),
                           "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0")
        try:
            return wb.newest().archive_url
        except waybackpy.exceptions.WaybackError:
            return False

    def build_wayback(self, url, ind=None, code=None, template=None):
        content_changed = False
        date_format = '%B %Y'
        wb = waybackpy.Url(str(url),
                           "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0")
        if code:
            try:
                archive_url = wb.newest().archive_url
                print(archive_url)
                date_format = '%B %Y'
                if archive_url:
                    code.replace(template,
                                 str(template) + "{{dead link|date=" + datetime.now().strftime(date_format)
                                 + "|url=" + archive_url + "|bot=TweetCiteBot}}")
                    content_changed = True
                else:
                    code.replace(template,
                                 str(template) + "{{dead link|date=" + datetime.now().strftime(date_format)
                                 + "|fix-attempted=yes" + "|bot=TweetCiteBot}}")
                    content_changed = True
                return [content_changed, code]
            except waybackpy.exceptions.WaybackError:
                code.replace(template,
                             str(template) + "{{dead link|date=" + datetime.now().strftime(date_format)
                             + "|fix-attempted=yes" + "|bot=TweetCiteBot}}")
                return [content_changed, code]
        else:
            try:
                archive_url = wb.newest().archive_url
                print(archive_url)
                date_format = '%B %Y'

                if archive_url:
                    text = re.sub(ind.group(0),
                                  ind.group(0) + "{{dead link|date=" + datetime.now().strftime(date_format)
                                  + "|url=" + archive_url + "|bot=TweetCiteBot}}", text)
                    content_changed = True
                else:
                    text = re.sub(ind.group(0),
                                  ind.group(0) + "{{dead link|date=" + datetime.now().strftime(date_format)
                                  + "|fix-attempted=yes" + "|bot=TweetCiteBot}}", text)
                    content_changed = True
            except waybackpy.exceptions.WaybackError:
                text = re.sub(ind.group(0), ind.group(0) + "{{dead link|date=" + datetime.now().strftime(date_format)
                              + "|fix-attempted=yes" + "|bot=TweetCiteBot}}", text)
                content_changed = True
                return [content_changed, code]

    def truncateUTF8length(self, unicodeStr, maxsize):
        return str(unicodeStr.encode("utf-8")[:maxsize], "utf-8", errors="ignore")
