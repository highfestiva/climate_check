#!/usr/bin/env python3
# -*- coding:utf-8 -*-

import argparse
import calendar
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from glob import glob
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import os
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
import requests
from urllib.request import urlretrieve


data_path = 'smhi_data/'
smhi_stations_url = 'https://opendata-download-metobs.smhi.se/api/version/1.0/parameter/22.json'
banner = '''
Climate check v0.4 using SMHI air temperature data.

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
    try:
        urlretrieve(url, filename)
    except Exception as e:
        print(type(e), e)


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
    executor = ThreadPoolExecutor(max_workers=20)
    for r in executor.map(download_station_data, stations_data['station']):
        _ = r
    print()


def load_smhi_csv(fn):
    '''Load single CSV, containing historical temperature data for a single station, in SMHI's
       format. The format is not very specific, so using brute force.

       This function returns the station name, its historical temperatures and some meta data,
       such as altitude, latitude and longitude.
       '''
    lines = open(fn, encoding='utf-8-sig').read().splitlines()
    location = lines[1].split(';')[0] # name of place on second row, first column
    altitude = latitude = longitude = None
    prevline = ''
    for line in lines[3:]:
        cols = line.split(';')
        try:
            if 'longitud' in prevline.lower():
                altitude,latitude,longitude = [float(c) for c in cols[-3:]]
            time,temp = cols[0], cols[3]
            if not time and not temp:
                continue # just ignore missing data points
            date,_,_ = time.partition(' ') # pick date
            temp = float(temp)
            times.append(date)
            temps.append(temp)
        except Exception as e:
            times = []
            temps = []
        prevline = line
    times = pd.DatetimeIndex(times).tz_localize('Europe/Stockholm', ambiguous=True)
    df = pd.DataFrame({'temp':temps}, index=times)
    return { 'station': location,
             'temperature': df,
             'altitude': altitude,
             'latitude': latitude,
             'longitude': longitude, }


def largest_consecutive_block(ser):
    sparse = pd.arrays.SparseArray(ser)
    spidx = sparse.sp_index.to_block_index()
    block_locs = list(zip(spidx.blocs, spidx.blengths))
    if not block_locs:
        return ser.iloc[:0]
    largest = max(block_locs, key=lambda e:e[1])
    i,l = largest
    return ser.iloc[i:(i+l-1)]


def pos_adjust_temp(df, pos_corr):
    '''Adjust temperatures based on linear regression of altitude and latitude.'''
    reg = LinearRegression()
    reg.fit(pos_corr[['altitude','latitude']], pos_corr['avg_temp'])
    c_altitude,c_latitude = reg.coef_
    c_altitude = min(0.0, c_altitude) # altitude correlates negatively, or not at all
    c_latitude = min(0.0, c_latitude) # latitude correlates negatively (in the nothern hemisphere), or not at all
    adj_temp = df['temp'].copy()
    avg_alt = df['altitude'].mean()
    avg_lat = df['latitude'].mean()
    # remove the correlation, so when there are more stations in the north, the temperature
    # will be adjusted upwards, and vice versa
    adj_temp -= (df['altitude']-avg_alt) * c_altitude
    adj_temp -= (df['latitude']-avg_lat) * c_latitude
    return adj_temp


def load_data(options):
    '''loads and combines data for all stations. Data is not combined straight off, as stations naturally yield
       different temperatures depending on location, etc. Instead I diff every month with the previous month;
       the relative temperature change should be more stable across the country.'''
    print('loading station data:')
    months = pd.date_range('1700-01', datetime.today(), freq='MS', tz='Europe/Stockholm', ambiguous=True)
    total = pd.DataFrame(index=months) # the combined data for all measurements
    total['temp'] = 0.0
    total['tempnum'] = 0
    total['altitude'] = 0.0
    total['latitude'] = 0.0
    total['longitude'] = 0.0
    total['diff'] = 0.0
    total['diffnum'] = 0
    pos_corr = pd.DataFrame(columns=['avg_temp','altitude','latitude']) # adjust for altitude and latitude
    globs = glob(data_path+'*.csv')
    for i,fn in enumerate(globs):
        if options.quick_test and i > 50:
            break
        res = load_smhi_csv(fn)
        title = res['station']
        df = res['temperature']
        print('\r  %i%%  %s                   ' % (100*(i+1)//len(globs), title), end='', flush=True)
        # absolute temperatures, for annual comparison
        total['raw'] = np.nan
        total['raw'] = df['temp']
        has_data = total['raw'] > -1e3
        total.loc[has_data, 'temp'] += total['raw']
        total.loc[has_data, 'tempnum'] += 1
        # add meta data on positions where we have temperature data
        total.loc[has_data, 'altitude'] += res['altitude']
        total.loc[has_data, 'latitude'] += res['latitude']
        total.loc[has_data, 'longitude'] += res['longitude']
        # correct for altitude and latitude
        longtemp = largest_consecutive_block(total['raw'])
        if len(longtemp) >= 12: # need at least a year
            l = len(longtemp)
            l -= l%12 # average temperature requires an even number of years
            longtemp = longtemp.iloc[:l]
            pos_corr.loc[len(pos_corr)] = longtemp.mean(), res['altitude'], res['latitude']
        # add difference for total time comparison (as temperatures will vary north to south)
        total['raw'] = np.nan
        total['raw'] = df['temp'].diff()
        has_data = total['raw'] > -1e3
        total.loc[has_data, 'diff'] += total['raw']
        total.loc[has_data, 'diffnum'] += 1
    total['diff'] /= total['diffnum']
    total['temp'] /= total['tempnum']
    total['altitude'] /= total['tempnum']
    total['latitude'] /= total['tempnum']
    total['longitude'] /= total['tempnum']
    print('\n  %i stations counted.' % len(globs))
    total['adjusted_temp'] = pos_adjust_temp(total, pos_corr)
    return total


def plot_total_time(df):
    df = df.dropna(subset=['adjusted_temp']).copy()
    df['Annual temperature cycle'] = df['adjusted_temp']
    # Climate uses 30 years mean: https://www.noaa.gov/education/resource-collections/climate/climate-data-monitoring
    df['30 year mean'] = df['30yr'] = df['Annual temperature cycle'].rolling(30*12).mean()
    df = df.dropna(subset=['30yr'])
    start_mean_temp = df['30yr'].iloc[0]
    end_mean_temp = df['30yr'].iloc[-1]
    temp_diff = end_mean_temp - start_mean_temp
    date = str(df.index[0])
    date = date.split('-')[0]
    title = 'Average air temperature in Sweden is up by %.1f degrees C since %s.' % (temp_diff, date)
    print(title)
    fig,ax = plt.subplots(num='Average air temperature in Sweden over time')
    ax.set_title(title)
    df = df.reset_index()
    cols = ['time'] + list(df.columns[1:])
    df.columns = cols
    df.plot(x='time', y='Annual temperature cycle', color='#dddddd', ax=ax)
    df.plot(x='time', y='30 year mean', ax=ax)


def plot_year_cycles(df):
    df_dates = df.dropna(subset=['adjusted_temp'])
    next_year = pd.Timestamp(datetime.today()).tz_localize('Europe/Stockholm') + pd.Timedelta(days=365)
    next_decade = pd.Timestamp(datetime.today()).tz_localize('Europe/Stockholm') + pd.Timedelta(days=10*365)
    years = pd.date_range(df_dates.index[0], next_year, freq='YS')
    start_year = years[0].year // 10 * 10 # start of decade
    first_decade = pd.Timestamp('%s-01-01'%start_year).tz_localize('Europe/Stockholm')
    decades = pd.date_range(first_decade, next_decade, freq='10YS')
    fig,ax = plt.subplots(num='Annual air temperature cycles per decade in Sweden')
    title = '%s decades between %s (blue) - %s (red)' % (len(decades)-1, str(decades[0]).split('-')[0], str(decades[-1]).split('-')[0])
    ax.set_title(title)
    cmap = plt.get_cmap('coolwarm')
    colors = [cmap(i) for i in np.linspace(0, 1, len(decades)-1)]
    for i,from_decade in enumerate(decades[:-1]):
        to_decade = decades[i+1]
        df1 = df[(df.index>=from_decade) & (df.index<to_decade)].copy()
        df1['Month'] = [int(str(d).split('-')[1]) for d in df1.index]
        df2 = df1.groupby('Month').mean()
        df2.plot(y='adjusted_temp', ax=ax, legend=False, color=colors[i])
    def func_format(x,pos):
        m = max(1, min(12, int(x)))
        return calendar.month_abbr[m]
    ax.xaxis.set_major_formatter(FuncFormatter(func_format))
    ax.xaxis.set_ticks(np.arange(1, 12+1))


def plot_position(df):
    fig,ax = plt.subplots(nrows=2)
    ax1,ax2 = ax
    fig.canvas.set_window_title('Average weather station position over time in Sweden')
    df.plot(y='altitude', ax=ax1, label='Average station altitude (m above sea level)')
    df.plot(y='latitude', ax=ax2, label='Average station latitude (60° N is near Uppsala)')


def main():
    print(banner)

    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh-data', action='store_true', default=False, help='download new temperature data from SMHI')
    parser.add_argument('--quick-test', action='store_true', default=False, help='only load small portion of data (for testing something quickly)')
    options = parser.parse_args()

    if len(glob(data_path+'*.csv')) < 5 or options.refresh_data:
        download_data()

    df = load_data(options)

    plot_total_time(df)
    plot_year_cycles(df)
    # plot_position(df)
    plt.show()


if __name__ == '__main__':
    main()
