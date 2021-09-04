import mwparserfromhell
import tsd_utils.templates
from tsd_utils.check_tweet import CheckTweet
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
                    tweet = CheckTweet(match.group(2))
                    if tweet:  # tweet is live
                        has_archive_url = False
                        content_changed = True
                        tweet_obj = tweet.clean_tweet()
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
                            tweet_obj += tweet.gen_date(use_mdy)
                            tweet_obj += "}}"
                    else:  # tweet is dead
                        date_format = '%B %Y'
                        if not template.has("archiveurl") or not template.has(
                                'archive-url'):  # isnt live and nothing exists
                            archive_url = tweet.is_wayback_live(url)

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

    #what_to_search = r'<ref>(?: +)?\[?(?:(?:\s)*https?:\/\/)?(?:www\.)?(?:\s)*?twitter\.com\/(?:#!\/)?@?([^\/\?\s]*)\/status\/([{\d+:\d+]+)(?:\?s=\d+?)?(?: +)?<\/ref>'
    what_to_search = r'<ref>(?: +)?\[?(?:(?:\s)*https?:\/\/)?(?:www\.)?(?:\s)*?(?:mobile\.)?twitter\.com\/(?:#!\/)?@?([^\/\?\s]*)\/status\/([{\d+:\d+]+)(?:\?s=\d+?)?(?: +)?(?: +)?(?:\{\{bare url inline\|date=\w+ \d+\}\})?<\/ref>'
    matches = re.finditer(what_to_search, str(text), flags=re.IGNORECASE)
    for ind in matches:
        dead = False

        tweet = CheckTweet(ind.group(2))
        # tweet = api.GetStatus(ind.group(2))
        if tweet:  # tweet live
            has_archive_url = False
            verbose = False
            tweet_obj = "<ref>"
            tweet_obj += tweet.clean_tweet()
            date_format = '%-d %B %Y'
            if use_mdy:
                date_format = '%B %-d, %Y'
            tweet_obj += tweet.gen_date(use_mdy)
            tweet_obj += "}}</ref>"
            text = re.sub(re.escape(ind.group(0)), tweet_obj, text, flags=re.UNICODE)
            if not content_changed:
                content_changed = True
        else:  # tweet dead
            print("Tweet dead")
            pass
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
