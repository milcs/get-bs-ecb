from contextlib import suppress
from selenium import webdriver
from selenium.webdriver.common.proxy import Proxy, ProxyType
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import pickle
import re
import os
import sys
import time
import signal
import datetime
import requests
from lxml import objectify
from tqdm import tqdm

__VERSION__ = '2.0'


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def load_cookies(path):
    with open(path, 'rb') as f:
        cookies = pickle.load(f)
    return cookies


def set_cookies(driver, cookies):
    for cookie in cookies:
        driver.add_cookie(cookie)

def get_driver(headless=True):
    """Create firefox driver
    """
    options = Options()
    if headless:
        options.add_argument("--headless")
    fp = webdriver.FirefoxProfile()
    gecko_path = os.path.join(os.path.dirname(__file__), 'driver/geckodriver')
    # Default timeout=30
    return webdriver.Firefox(firefox_profile=fp, options=options, executable_path=gecko_path, timeout=60)

def initial_open(headless=True):
    try:
        driver = get_driver(headless)
    except Exception as err:
        eprint(f'Unable to open the driver: {err}')
        return

    # trying to open investors.com, set up the cookies and navigate to research page
    try:
        eprint('Loading www.bsi.si..')
        target_page = 'https://www.bsi.si/statistika/devizni-tecaji-in-plemenite-kovine/dnevna-tecajnica-referencni-tecaji-ecb'
        driver.get(target_page)
        #cookies_path = os.path.join(os.path.dirname(__file__), 'cookies')
        #cookies = load_cookies(cookies_path)
        #set_cookies(driver, cookies)
        time.sleep(2)

    except Exception as err:
        eprint(f'Error: unable to open research page: {err}')
        return
    return driver

def scrape(dates, headless=True, session_id=None, executor_url=None):
    retries = 3
    if session_id is None:
        headless_str = 'HEAD'
        if headless:
            headless_str = 'HEADLESS'
        eprint('Opening new session: %s mode' % headless_str)
        driver = initial_open(headless)

        while len(dates) > 0 and retries > 0:
            # trying to get the entire symbol
            try:
                date = dates[0]
                # locate search field
                field = driver.find_element_by_id('datepicker')
                driver.execute_script(f'arguments[0].value = "{date}";', field)

                go_button = driver.find_element_by_class_name('button')
                # eprint(f'Loading page results for {date}..')
                # click the button to load symbol stats
                go_button.click()

                exchange_date = driver.find_element_by_xpath('/html/body/div[4]/div[2]/div/div[2]/div/div[1]/form/div/div[2]/p/span')
                valuta = driver.find_element_by_xpath('/html/body/div[4]/div[2]/div/div[2]/div/div[1]/table/tbody/tr[1]/td[3]')
                sifra = driver.find_element_by_xpath('/html/body/div[4]/div[2]/div/div[2]/div/div[1]/table/tbody/tr[1]/td[4]')
                tecaj = driver.find_element_by_xpath('/html/body/div[4]/div[2]/div/div[2]/div/div[1]/table/tbody/tr[1]/td[5]')

                # Web site lists tecaj in slovenian decimal format:
                # 1,1006 -> 1.1006
                tecaj_str = tecaj.text.replace(',', '.')
                sep = '\t'
                print(f'{sep.join([date, exchange_date.text, valuta.text, tecaj_str])}')

            except Exception as err:
                retries -= 1
                eprint(f'An error occurred when trying to get info for date {date}: {err}')
                # driver.get('http://research.investors.com/stock-checkup/')
            driver.back()
            dates.pop(0)
            retries = 3


def scrape_xml(dates, oznaka='USD'):
    """"scrape_xml lists the exchange rate for a list of requested dates by 
    GETing the data from the XML published by www.bsi.si  
    
    Step 1: Download the XML with tecajnica
    Sample XML snippet:
     <DtecBS xsi:schemaLocation="http://www.bsi.si http://www.bsi.si/_data/tecajnice/DTecBS-l.xsd">
     <tecajnica datum="2007-01-01">
     <tecaj oznaka="USD" sifra="840">1.3170</tecaj>
    
    Step 2: Extract the exchange rate
        - Loop for all published dates
        - Fill in the rate for missing dates (e.g. weekends, holidays) by using previous available rate 
    
    Print to console: tab separated 
    header: date date_as_of currency rate
     
    Example output:
    Start Date:
    End Date:
    Days to fetch: 353
    100%|██████████| 4348/4348 [00:00<00:00, 99026.04it/s]
    2023-01-02	2023-01-02	USD	1.0683
    2023-01-03	2023-01-03	USD	1.0545
    2023-01-04	2023-01-04	USD	1.0599
    2023-01-05	2023-01-05	USD	1.0601
    2023-01-06	2023-01-06	USD	1.0500
    2023-01-07	2023-01-06	USD	1.0500
    2023-01-08	2023-01-06	USD	1.0500 
     
    """""
    # Preconfigured vars
    xml_url = 'https://www.bsi.si/_data/tecajnice/dtecbs-l.xml'
    xml_local_file = 'logs/dtecbs-l.xml'
    header_list = ['datum', 'on_datum', 'oznaka', 'tecaj']
    sep='\t'

    # Step 1: Download the XML with tecajnica
    response = requests.get(xml_url)

    # Save XML data file to a local file (for reference)
    with open(xml_local_file, 'w') as f:
        f.write(str(response.content))

    # Step 2:  Extract the exchange rate
    main = objectify.fromstring(response.content)

    currency_list = list()

    # Create a dict from date list using date as key
    date_dict = { d: {'datum': d} for d in dates}

    # Process each xml element
    tecajnica_list = main.tecajnica
    for tecajnica in tqdm(tecajnica_list):
        datum = tecajnica.get('datum')
        if datum not in dates:
            continue

        for tecaj in tecajnica.tecaj:
            currency = tecaj.get('oznaka')
            # Add the currency to currency_list
            if currency not in currency_list:
                currency_list += currency,
            if currency == oznaka:
                tecaj_val = tecaj.text
                date_dict[datum]['oznaka'] = oznaka
                date_dict[datum]['tecaj'] = tecaj_val

    # Populate missing dates with previous date value and add "on_datum"
    date_last = None
    rate_list = list()
    for date in tqdm(date_dict.keys()):
        tecaj = date_dict[date]
        date_dict[date]['on_datum'] = date
        if 'oznaka' not in tecaj and date_last is not None:
            date_dict[date] = date_dict[date_last]
            date_dict[date]['datum'] = date
            date_dict[date]['on_datum'] = date_last
        else:
            date_last = date
        # print(date_dict[date])
        t = date_dict[date]
        with suppress(KeyError):
            rate_list += [t['datum'], t['on_datum'], t['oznaka'], t['tecaj']],

    # Print input params and misc:
    print(f'Fetching Exchange Rates for {oznaka}')
    print(f'  Start date: {dates[0]}')
    print(f'    End date: {dates[-1]}')
    print(f'Available currencies: {currency_list}')

    # Print header
    print(sep.join(header_list))

    # Print data
    for day_rate in rate_list:
        print(sep.join(day_rate))


def signal_handler(signal, frame):
    """"Exit after CTRL-C - stop the thread."""
    eprint('\nCTRL-C Detected. Aborting...')
    eprint('Bye.')
    exit(-1)


# Main Section
if __name__ == "__main__":
    # Hook signal_handler custom function to CTRL-C signal.
    signal.signal(signal.SIGINT, signal_handler)

    # Select target currency to extract/
    # The list of choices for the currency as of 2023-12-20 are:
    # ['USD', 'JPY', 'BGN', 'CZK', 'DKK', 'GBP', 'HUF', 'PLN', 'RON', 'SEK', 'ISK', 'CHF', 'NOK', 'TRY', 'AUD', 'BRL',
    #  'CAD', 'CNY', 'HKD', 'IDR', 'ILS', 'INR', 'KRW', 'MXN', 'MYR', 'NZD', 'PHP', 'SGD', 'THB', 'ZAR']

    target_currency = 'USD'

    #  Set START Date
    start_date = datetime.datetime.strptime('01.01.2023', '%d.%m.%Y')

    # Set END Date, or keep today() code line
    # end_date = datetime.datetime.strptime('12.12.2018', '%d.%m.%Y')
    end_date = datetime.datetime.today()

    # Calculate number of days between the start/end date
    dt = end_date - start_date
    print(f'Days to fetch: {dt.days}')
    num_days = dt.days + 1
    dates_list = [(start_date + datetime.timedelta(days=x)) for x in range(0, num_days)]
    dates_list.sort()
    dates_list_dmy = [x.strftime('%d.%m.%Y') for x in dates_list]
    dates_list_ymd = [x.strftime('%Y-%m-%d') for x in dates_list]

    # print(date_list)
    if __VERSION__ == '1.0':
        scrape(dates_list_dmy, False, None, None)
    elif __VERSION__ == '2.0':
        scrape_xml(dates_list_ymd, oznaka=target_currency)

# Last line
