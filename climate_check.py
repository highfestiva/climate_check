#!/usr/bin/env python3

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from dateutil.relativedelta import relativedelta
import dateutil.parser
from glob import glob
import matplotlib.pyplot as plt
import os
import pandas as pd
import requests
from urllib.request import urlretrieve


data_path = 'smhi_data/'
smhi_stations_url = 'https://opendata-download-metobs.smhi.se/api/version/1.0/parameter/22.json'
banner = '''
Climate check v0.1 using SMHI air temperature data.

  This check might be considered unscientific as I am only using Swedish air temperature,
  not world-wide air and ocean temperatures.

  On the other hand, we can be pretty sure it hasn't been tampered with, as whistle
  blower and 2014 U.S. Department of Commerce Gold Medal winner John Bates exposed
  within NOAA in February 2017.

  Feel free to play around with and change to, or add, your local weather service!
'''


def download_station_data(station):
    print('\r  %s           ' % station['title'], end='', flush=True)
    url = 'https://opendata-download-metobs.smhi.se/api/version/1.0/parameter/22/station/%s/period/corrected-archive/data.csv' % station['id']
    filename = data_path + '%s.csv' % station['id']
    urlretrieve(url, filename)


def download_data():
    print('downloading new data from SMHI:')
    # download stations before erasing any existing data, so we're not left stranded
    stations_data = requests.get(smhi_stations_url).json()
    for fn in glob(data_path+'*.csv'):
        os.remove(fn)
    try: os.mkdir(data_path)
    except FileExistsError: pass
    # download data per each station
    print(' ', stations_data['summary'])
    executor = ThreadPoolExecutor(max_workers=10)
    for r in executor.map(download_station_data, stations_data['station']):
        _ = r
    print()


def load_smhi_csv(fn):
    '''Load CSV temperature data in SMHI's format. The format is not very specific, so using brute force.'''
    lines = open(fn, encoding='utf-8-sig').read().splitlines()
    location = lines[1].split(';')[0] # name of place on second row, first column
    for line in lines:
        cols = line.split(';')
        try:
            time,temp = cols[1], cols[3]
            if not time and not temp:
                continue # just ignore missing data points
            times.append(dateutil.parser.parse(time).replace(day=1)+relativedelta(months=1, days=-1))
            temps.append(float(temp))
        except Exception as e:
            times = []
            temps = []
    df = pd.DataFrame({'temp':temps}, index=times)
    return location, df


def load_data():
    '''loads and combines data for all stations. Data is not combined straight off, as stations naturally yield
       different temperatures depending on location, etc. Instead I diff every month with the previous month;
       the relative temperature change should be more stable across the country.'''
    print('loading station data:')
    months = pd.date_range('1700-01', datetime.today(), freq='M')
    total = pd.DataFrame(index=months) # the combined data for all measurements
    total['diff'] = 0.0
    total['num'] = 0
    globs = glob(data_path+'*.csv')
    for i,fn in enumerate(globs):
        title,df = load_smhi_csv(fn)
        print('\r  %i %%  %s                 ' % (100*i//len(globs), title), end='', flush=True)
        total['raw'] = df['temp'].diff() # add difference, as temperatures will vary north to south
        total['raw'].fillna(0.0, inplace=True)
        total['diff'] += total['raw']
        total['raw'] = (df['temp']>-1e3).astype(float) # count how many (for arithmetic mean)
        total['raw'].fillna(0.0, inplace=True)
        total['num'] += total['raw']
    total['diff'] /= total['num']
    print('\n  %i stations counted.' % len(globs))
    return total.dropna(subset=['diff'])


def plot(df):
    df['annual temperature cycle'] = df['diff']
    df['10 year mean'] = df['10yr'] = df['diff'].rolling(10*12).mean()
    df = df.dropna()
    title = 'Air temperature in Sweden is up by %.1f degrees C since %s.' % (df['10yr'].iloc[-1]-df['10yr'].iloc[0], str(df.index[0]).split('-')[0])
    print(title)
    fig,ax = plt.subplots()
    ax.set_title(title)
    fig.canvas.set_window_title('Temperature across Sweden')
    df.plot(x=df.index, y='annual temperature cycle', color='#dddddd', ax=ax)
    df.plot(x=df.index, y='10 year mean', ax=ax)
    plt.show()


def main():
    print(banner)

    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh-data', action='store_true', default=False, help='download new temperature data from SMHI')
    options = parser.parse_args()

    if len(glob(data_path+'*.csv')) < 5 or options.refresh_data:
        download_data()

    df = load_data()

    plot(df)


if __name__ == '__main__':
    main()
