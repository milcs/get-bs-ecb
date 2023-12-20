# Description:
**BSI Exchange Rates Extractor**

As part of my business I am in need of official BSI EUR/USD exchange rates to accompany my invoices. This is my script that extracts the data from the XML that is published by [Bank of Slovenia](https://www.bsi.si) at [url](https://www.bsi.si/_data/tecajnice/dtecbs-l.xml).

## How to Use:
Edit the [get-bs-ecb.py](path-to-your-script) Python file, navigate to the main function, and update your target variables: target_currency, start_date, end_date.

Main snippet:
```python
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
```

Output example:
```yaml
Fetching Exchange Rates for USD
  Start date: 2023-01-01
    End date: 2023-12-20
Available currencies: ['USD', 'JPY', 'BGN', 'CZK', 'DKK', 'GBP', 'HUF', 'PLN', 'RON', 'SEK', 'ISK', 'CHF', 'NOK', 'TRY', 'AUD', 'BRL', 'CAD', 'CNY', 'HKD', 'IDR', 'ILS', 'INR', 'KRW', 'MXN', 'MYR', 'NZD', 'PHP', 'SGD', 'THB', 'ZAR']
datum	on_datum	oznaka	tecaj
2023-01-02	2023-01-02	USD	1.0683
2023-01-03	2023-01-03	USD	1.0545
2023-01-04	2023-01-04	USD	1.0599
```

Run example:
```shell
python3 get-bs-ecb.py
```

## Installation
This script requires a couple of additional Python packages listed in the requirements.txt file.

Install by running:
```shell
python3 -m pip install -r requirements.txt
```