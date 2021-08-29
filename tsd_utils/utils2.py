import mwparserfromhell
import tsd_utils.templates
from itertools import tee, islice, zip_longest
import re
import waybackpy
from datetime import *
from dateutil.parser import *
from twitter.error import TwitterError
import textwrap, twitter, pywikibot


def call_home(site):
    page = pywikibot.Page(site, 'User:TweetCiteBot/status')
    text = page.text
    if "false" in text.lower():
        return False
    return True


def allow_bots(text, user):
    user = user.lower().strip()
    text = mwparserfromhell.parse(text)
    for tl in text.filter_templates():
        if tl.name in ('bots', 'nobots'):
            break
    else:
        return True
    for param in tl.params:
        bots = [x.lower().strip() for x in param.value.split(",")]
        if param.name == 'allow':
            if ''.join(bots) == 'none': return False
            for bot in bots:
                if bot in (user, 'all'):
                    return True
        elif param.name == 'deny':
            if ''.join(bots) == 'none': return True
            for bot in bots:
                if bot in (user, 'all'):
                    return False
    return True


def get_next_iter_item(some_iterable, window=1):
    """
    Get the item that will be in next iteration of the loop.
    This will be useful for finding {{dead link}} templates.
    This code is adapted from an answer to a StackOverflow question by user nosklo
    https://stackoverflow.com/questions/4197805/python-for-loop-look-ahead/4197869#4197869
    @param some_iterable Thing to iterate over
    @param window How far to look ahead
    """
    items, nexts = tee(some_iterable, 2)
    nexts = islice(nexts, window, None)
    return zip_longest(items, nexts)


def convert(text, api, archive_urls):
    """
    Converts use of {{cite web}} for tweets (if present) to using {{cite tweet}}.
    @param text Page text to go over
    @param api Twitter API instance
    @returns [content_changed, content] Whether content was changed,
    (if former true, modified) content.
    """
    wikicode = mwparserfromhell.parse(text)
    templates = wikicode.filter_templates()
    content_changed = False
    code = mwparserfromhell.parse(text)
    dead_link = False
    use_mdy = False
    verbose = False
    for template, next_template in get_next_iter_item(
            code.filter_templates()):  # Tracklist, Track, Soundtrack, Tlist, Track list
        if template.name.lower() in tsd_utils.templates.date_types:
            use_mdy = True

        if template.name.lower() in tsd_utils.templates.templates_to_search_through:
            if template.has("url"):
                url = template.get("url").value
                match = re.search(
                    r'(?:(?:\s)*https?:\/\/)?(?:www\.)?(?:\s)*?twitter\.com\/(?:#!\/)?@?([^\/\?\s]*)\/status\/([{\d+:\d+]+)',
                    str(url))
                if match:  # it is a twitter URL
                    if next_template:
                        if next_template.name.matches(
                                "dead link"):  # TODO: Expand to cover variations/aliases of {{dead link}}
                            # Play it safe and leave this template as the next one
                            # shouldn't be a deadlink (if it is, doing all this for nothing)
                            print("FOUND DEADLINK......SKIPPING!")
                            continue
                    try:
                        if not template.has("archiveurl") or not template.has('archive-url'):
                            tweet = api.GetStatus(match.group(2))
                        if tweet:
                            has_archive_url = False
                            content_changed = True
                            if verbose:
                                print(match.group(0))
                            # url_reg  = r'[a-z]*[:.]+\S+'
                            url_reg = r'((?:\s)*https?:\/\/)?(?:www\.)?(?:\s)*?t\.co\/([a-zA-Z0-9])*'
                            sec_pattern = r'/\r|\n/'
                            #text = re.sub(url_reg, '', tweet.text)
                            #text = re.sub(sec_pattern, ' ', text)
                            #tweet_text = textwrap.shorten(text, width=40, placeholder="...")
                            tweet_text = re.sub(url_reg, '', tweet.text)
                            tweet_text = re.sub(sec_pattern, ' ', tweet_text)
                            tweet_text = textwrap.shorten(tweet_text, width=40, placeholder="...")
                            if verbose:
                                print(tweet_text)
                            tweet_obj = "{{cite tweet|number=" + str(
                                match.group(2)) + "|user=" + tweet.user.screen_name + "|title=" + tweet_text
                            tweet_accessdate = tweet_archivedate = tweet_language = tweet_archiveurl = tweet_date = None
                            if template.has("accessdate") or template.has("access-date"):
                                # tweet_accessdate = template.get("accessdate").value
                                tweet_obj += "|accessdate=" + str(template.get("accessdate").value)
                                if verbose:
                                    print("Has accessdate")
                            if template.has("archivedate") or template.has("archive-date"):
                                if verbose:
                                    print("Has archive date")
                                #    tweet_archivedate = template.get("archivedate").value
                                tweet_obj += "|archivedate=" + str(template.get("archivedate").value)
                            if template.has("language"):
                                # tweet_language = template.get("language").value
                                tweet_obj += "|language=" + str(template.get("language").value)
                                if verbose:
                                    print("Has language")
                            if template.has("archiveurl") or template.has('archive-url'):
                                has_archive_url = True
                                # tweet_archiveurl = template.get("archiveurl").value
                                tweet_obj += "|archiveurl=" + str(template.get("archiveurl").value)
                                if verbose:
                                    print("Has archiveurl")
                            if template.has("date"):
                                # tweet_date = template.get("date").value
                                tweet_obj += "|date=" + str(template.get("date").value)
                                if verbose:
                                    print("Has date")
                            else:
                                # For reference: http://strftime.org
                                date_format = '%-d %B %Y'
                                if use_mdy:
                                    date_format = '%B %-d, %Y'
                                tweet_obj += "|date=" + parse(tweet.created_at).strftime(date_format)
                            # tweet_obj += "}}"
                            if not has_archive_url and archive_urls:
                                # wb = waybackpy.Url
                                wb = waybackpy.Url(str(url),
                                                   "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0")
                                archive_url = wb.newest().archive_url
                                print(archive_url)
                                if archive_url:
                                    tweet_obj += "|archive-url=" + archive_url
                                    tweet_obj += "|archivedate=" + datetime.now().strftime('%B %Y')
                                    # pass
                                #    code.replace(template, str(template) + "{{dead link|date=" + datetime.now().strftime(date_format)
                                #    + "|url=" + archive_url + "|bot=TweetCiteBot}}")

                                #    code.replace(template, str(template) + "{{dead link|date=" + datetime.now().strftime(date_format)
                                #    + "|fix-attempted=yes" + "|bot=TweetCiteBot}}")
                            tweet_obj += "}}"

                            code.replace(template, tweet_obj)
                            content_changed = True
                    except TwitterError as err:
                        # TODO: Somewhere here we should try to look to archive,
                        # since Tweet clearly doesn't exist.
                        # TODO: Figure out wayback in python
                        if err.message[0].get('code') == 144:
                            print("Tweet dead")
                            # wb = WaybackClient
                            # archive_url = wb.closest(str(url))
                            date_format = '%B %Y'
                            try:
                                wb = waybackpy.Url(str(url),
                                                   "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0")
                                archive_url = wb.newest().archive_url
                                print(archive_url)

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
                            except waybackpy.exceptions.WaybackError:
                                code.replace(template,
                                             str(template) + "{{dead link|date=" + datetime.now().strftime(date_format)
                                             + "|fix-attempted=yes" + "|bot=TweetCiteBot}}")
                            # print(archive_url)
    what_to_search = r'<ref>(?: +)?\[?(?:(?:\s)*https?:\/\/)?(?:www\.)?(?:\s)*?twitter\.com\/(?:#!\/)?@?([^\/\?\s]*)\/status\/([{\d+:\d+]+)(?:\?s=\d+?)?(?: +)?<\/ref>'
    matches = re.finditer(what_to_search, str(text))
    for ind in matches:
        dead = False
        try:
            tweet = api.GetStatus(ind.group(2))
            if tweet:
                has_archive_url = False
                verbose = False
                if verbose:
                    print(ind.group(0))
                # url_reg  = r'[a-z]*[:.]+\S+'
                url_reg = r'((?:\s)*https?:\/\/)?(?:www\.)?(?:\s)*?t\.co\/([a-zA-Z0-9])*'
                sec_pattern = r'/\r|\n/'
                tweet_text = re.sub(url_reg, '', tweet.text)
                tweet_text = re.sub(sec_pattern, ' ', tweet_text)
                tweet_text = textwrap.shorten(tweet_text, width=40, placeholder="...")

                if verbose:
                    print(tweet_text)
                tweet_obj = "<ref>{{cite tweet|number=" + str(
                    ind.group(2)) + "|user=" + tweet.user.screen_name + "|title=" + tweet_text
                tweet_accessdate = tweet_archivedate = tweet_language = tweet_archiveurl = tweet_date = None
                # For reference: http://strftime.org
                date_format = '%-d %B %Y'
                if use_mdy:
                    date_format = '%B %-d, %Y'
                tweet_obj += "|date=" + parse(tweet.created_at).strftime(date_format)
                if not has_archive_url and archive_urls:
                    # wb = wayback.Wayback()
                    # archive_url = wb.closest(str(url))
                    wb = waybackpy.Url(str(url), "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0")
                    try:
                        archive_url = wb.newest().archive_url
                        print(archive_url)
                        if archive_url:
                            tweet_obj += "|archive-url=" + archive_url
                            tweet_obj += "|archivedate=" + datetime.now().strftime('%B %Y')
                    except waybackpy.exceptions.WaybackError:
                        dead = True
                        # pass
                    #    code.replace(template, str(template) + "{{dead link|date=" + datetime.now().strftime(date_format)
                    #    + "|url=" + archive_url + "|bot=TweetCiteBot}}")

                    #    code.replace(template, str(template) + "{{dead link|date=" + datetime.now().strftime(date_format)
                    #    + "|fix-attempted=yes" + "|bot=TweetCiteBot}}")
                tweet_obj += "}}</ref>"
                #if dead:
                 #   text = re.sub(ind.group(0), tweet_obj + "{{dead link|date=" + datetime.now().strftime(date_format)
                  #      + "|fix-attempted=yes" + "|bot=TweetCiteBot})", text)
                text = re.sub(ind.group(0), tweet_obj, text)
                if not content_changed:
                    content_changed = True
        except TwitterError as err:
            try:
                wb = waybackpy.Url(str(url),
                                   "Mozilla/5.0 (Windows NT 5.1; rv:40.0) Gecko/20100101 Firefox/40.0")
                archive_url = wb.newest().archive_url
                print(archive_url)
                date_format = '%B %Y'

                if archive_url:
                    text = re.sub(ind.group(0), ind.group(0) + "{{dead link|date=" + datetime.now().strftime(date_format)
                                 + "|url=" + archive_url + "|bot=TweetCiteBot}}", text)
                    content_changed = True
                else:
                    text = re.sub(ind.group(0), ind.group(0) + "{{dead link|date=" + datetime.now().strftime(date_format)
                                 + "|fix-attempted=yes" + "|bot=TweetCiteBot}}", text)
                    content_changed = True
            except waybackpy.exceptions.WaybackError:
                code.replace(template,
                             str(template) + "{{dead link|date=" + datetime.now().strftime(date_format)
                             + "|fix-attempted=yes" + "|bot=TweetCiteBot}}")

    return [content_changed, text]


def save_edit(site, api, page, archive_urls, text):
    code = mwparserfromhell.parse(text)
    for template in code.filter_templates():
        if template.name.matches("nobots") or template.name.matches("Wikipedia:Exclusion compliant"):
            if template.has("allow"):
                if "TweetCiteBot" in template.get("allow").value:
                    break  # can edit
            print("\n\nPage editing blocked as template preventing edit is present.\n\n")
            return
    content_changed, text = convert(page.text, api,
                                    archive_urls)  # combine_converts(site, api, page, archive_urls, text)
    # print(content_changed)
    if content_changed:
        page.text = text
        if not call_home(site):
            raise ValueError("Kill switch on-wiki is false. Terminating program.")
        edit_summary = """Converted Tweet
         URLs to [[Template:Cite tweet|{{cite tweet}}]] Mistake? [[User talk:TheSandDoctor|msg TSD!]] (please mention that this is the PyEdition!)"""
        time = 0
        page.save(edit_summary)
        print("Saved")
