import mwparserfromhell
import tsd_utils.templates
from itertools import tee, islice, zip_longest
import re
import wayback
from datetime import *
from dateutil.parser import *
from twitter.error import TwitterError
import textwrap, twitter

def call_home(site):
    page = site.Pages['User:TweetCiteBot/status']
    text = page.text()
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


def convert(text,dry_run, api,archive_urls):
    """
    Converts use of {{cite web}} for tweets (if present) to using {{cite tweet}}.
    @param text Page text to go over
    @param dry_run boolean Whether or not this is a dry run (dry run = no live edit)
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
    for template, next_template in get_next_iter_item(code.filter_templates()):#Tracklist, Track, Soundtrack, Tlist, Track list
        if template.name.lower() in tsd_utils.templates.date_types:
            use_mdy = True

        if template.name.lower() in tsd_utils.templates.templates_to_search_through:
            if template.has("url"):
                url = template.get("url").value
                match = re.match(r'(?:(?:\s)*https?:\/\/)?(?:www\.)?(?:\s)*?twitter\.com\/(?:#!\/)?@?([^\/\?\s]*)\/status\/([{\d+:\d+]+)',str(url))
                if match:   # it is a twitter URL
                    if next_template:
                        if next_template.name.matches("dead link"): #TODO: Expand to cover variations/aliases of {{dead link}}
                            # Play it safe and leave this template as the next one
                            # shouldn't be a deadlink (if it is, doing all this for nothing)
                            print("FOUND DEADLINK......SKIPPING!")
                            continue
                    try:
                        tweet = api.GetStatus(match.group(2))
                        if tweet:
                            has_archive_url = False
                            content_changed = True
                            if verbose:
                                print(match.group(0))
                            #url_reg  = r'[a-z]*[:.]+\S+'
                            url_reg = r'((?:\s)*https?:\/\/)?(?:www\.)?(?:\s)*?t\.co\/([a-zA-Z0-9])*'
                            sec_pattern = r'/\r|\n/'
                            text   = re.sub(url_reg, '', tweet.text)
                            text = re.sub(sec_pattern, ' ', text)
                            tweet_text = textwrap.shorten(text,width=40,placeholder="...")
                            if verbose:
                                print(tweet_text)
                            tweet_obj = "{{cite tweet|number=" + str(match.group(2)) + "|user=" + tweet.user.screen_name + "|title=" + tweet_text
                            tweet_accessdate = tweet_archivedate = tweet_language = tweet_archiveurl = tweet_date = None
                            if template.has("accessdate") or template.has("access-date"):
                                #tweet_accessdate = template.get("accessdate").value
                                tweet_obj += "|accessdate=" + str(template.get("accessdate").value)
                                if verbose:
                                    print("Has accessdate")
                            if template.has("archivedate") or template.has("archive-date"):
                                if verbose:
                                    print("Has archive date")
                            #    tweet_archivedate = template.get("archivedate").value
                                tweet_obj += "|archivedate=" + str(template.get("archivedate").value)
                            if template.has("language"):
                                #tweet_language = template.get("language").value
                                tweet_obj += "|language=" + str(template.get("language").value)
                                if verbose:
                                    print("Has language")
                            if template.has("archiveurl"):
                                has_archive_url = True
                                #tweet_archiveurl = template.get("archiveurl").value
                                tweet_obj += "|archiveurl=" + str(template.get("archiveurl").value)
                                if verbose:
                                    print("Has archiveurl")
                            if template.has("date"):
                                #tweet_date = template.get("date").value
                                tweet_obj += "|date=" + str(template.get("date").value)
                                if verbose:
                                    print("Has date")
                            else:
                                #For reference: http://strftime.org
                                date_format = '%-d %B %Y'
                                if use_mdy:
                                    date_format = '%B %-d, %Y'
                                tweet_obj += "|date=" + parse(tweet.created_at).strftime(date_format)
                            #tweet_obj += "}}"
                            if not has_archive_url and archive_urls:
                                wb = wayback.Wayback()
                                archive_url = wb.closest(str(url))
                                print(archive_url)
                                if archive_url:
                                    tweet_obj += "|archive-url=" + archive_url
                                    tweet_obj += "|archivedate=" + datetime.now().strftime('%B %Y')
                                    #pass
                                #    code.replace(template, str(template) + "{{dead link|date=" + datetime.now().strftime(date_format)
                                #    + "|url=" + archive_url + "|bot=TweetCiteBot}}")

                                #    code.replace(template, str(template) + "{{dead link|date=" + datetime.now().strftime(date_format)
                                #    + "|fix-attempted=yes" + "|bot=TweetCiteBot}}")
                            tweet_obj += "}}"

                            code.replace(template, tweet_obj)
                            content_changed = True
                    except TwitterError as err:
                        #TODO: Somewhere here we should try to look to archive,
                        # since Tweet clearly doesn't exist.
                        # TODO: Figure out wayback in python
                        print("Clearly something went wrong with tweet " + str(err))
                        wb = wayback.Wayback()
                        archive_url = wb.closest(str(url))
                        print(archive_url)
                        date_format = '%B %Y'
                        if archive_url:
                            code.replace(template, str(template) + "{{dead link|date=" + datetime.now().strftime(date_format)
                            + "|url=" + archive_url + "|bot=TweetCiteBot}}")
                            content_changed = True
                        else:
                            code.replace(template, str(template) + "{{dead link|date=" + datetime.now().strftime(date_format)
                            + "|fix-attempted=yes" + "|bot=TweetCiteBot}}")
                            content_changed = True
                        #print(archive_url)


    return [content_changed, str(code)] # get back text to save


def getList():
    f = open("list of all articles containing links to tweets (unmarked up).txt", 'r')
    lst = f.read().split('\n')
    articles = []
    for l in lst:
        if not l is "":
            articles.append(l)
    return articles

def save_edit(page, utils, text):
     api = utils[1]
     site = utils[2]
     dry_run = utils[4]
     archive_urls = utils[3]
     original_text = text

     code = mwparserfromhell.parse(text)
     for template in code.filter_templates():
         if template.name.matches("nobots") or template.name.matches("Wikipedia:Exclusion compliant"):
             if template.has("allow"):
                 if "TweetCiteBot" in template.get("allow").value:
                     break # can edit
             print("\n\nPage editing blocked as template preventing edit is present.\n\n")
             return

     if not call_home(site):
        raise ValueError("Kill switch on-wiki is false. Terminating program.")
     edit_summary = """Converted Tweet
     URLs to [[Template:Cite tweet|{{cite tweet}}]] Mistake? [[User talk:TheSandDoctor|msg TSD!]] (please mention that this is the PyEdition!)"""
     time = 0
     while True:
         #content_changed = False
         #text = page.edit()
         #text = text.replace('[[Category:Apples]]', '[[Category:Pears]]')
         if time == 0:
             text = page.text()
         if time == 1:
        #     page = site.Pages[page.page_title]
             page.purge()
             original_text = site.Pages[page.page_title].text()
         content_changed, text = convert(original_text,dry_run, api, archive_urls)
         try:
             if dry_run:
                 print("Dry run")
                 #Write out the initial input
                 text_file = open("Input02.txt", "w")
                 text_file.write(original_text)
                 text_file.close()
                 #Write out the output
                 if content_changed:
                     text_file = open("Output02.txt", "w")
                     text_file.write(text)
                     text_file.close()
                 else:
                     print("Content not changed, don't print output")
                 break
             else:
                if verbose:
                    print("LIVE run")
                #print("Would have saved here")
                #break
                #TODO: Enable
                if not content_changed:
                    if verbose:
                        print("Content not changed, don't bother pushing edit to server")
                    break
                #break
                page.save(text, summary=edit_summary, bot=True, minor=True)
                #print(page.page_title)
                print("Saved page")
                if time == 1:
                    time = 0
                break
         except [[EditError]]:
             print("Error")
             time = 1
             time.sleep(5)   # sleep for 5 seconds, giving server some time before querying again
             continue
         except [[ProtectedPageError]] as e:
             print('Could not edit ' + page.page_title + ' due to protection')
             print(e)
         break
