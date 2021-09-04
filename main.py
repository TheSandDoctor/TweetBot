import sys, twitter, mwclient, configparser
from mwclient import *
import tsd_utils.utils
def main():
    site = mwclient.Site(('https', 'en.wikipedia.org'), '/w/')
    config = configparser.RawConfigParser()
    config.read('credentials.txt')
    try:
        site.login(config.get('enwiki', 'username'), config.get('enwiki', 'password'))
    except errors.LoginError as e:
        # print(e[1]['reason'])
        print(e)
        raise ValueError("Login failed.")
    api = twitter.Api(consumer_key='CUST_KEY',
                      consumer_secret='CUST_SECRET',
                      access_token_key='TOK_KEY',
                      access_token_secret='TOK_SECRET')


    counter = 0

    utils = [config, api, site, archive_urls]
    list = tsd_utils.utils.getList()


    while counter < pages_to_run:
        if offset > 0:
            offset -= 1
            if verbose:
                print("Skipped due to offset config")
            counter += 1
            continue
        print("Working with: " + list[counter])
        page = site.Pages[list[counter]]
        print(counter)
        text = page.text()
        try:
            tsd_utils.utils.save_edit(page, utils, text)  # config, api, site, text, dry_run)#, config)
            # time.sleep(0.5)    # sleep 1/2 second in between pages
        except ValueError as err:
            print(err)
        counter += 1

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted")
        sys.exit(0)