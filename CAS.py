import csv
import json
import re
import sys
import datetime
import requests
import os
import pandas as pd
from bs4 import BeautifulSoup
import numpy as np
from geopy.geocoders import Nominatim
from app_classes import *

import geopandas as gpd
import os
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Point, Polygon, LineString, shape
import fiona

from geopandas import GeoDataFrame

from pyproj import Proj, transform

from geopy.exc import GeocoderTimedOut

# Config parser was renamed in Python 3
try:
    import configparser
except ImportError:
    import ConfigParser as configparser

from app_classes import *

def create_csv(url, fname):

    '''
    Create a CSV file with information that can be imported into pandas DataFrame
    '''

    # avoid the issue on Windows where there's an extra space every other line
    if sys.version_info[0] == 2:  # Not named on 2.6
        access = 'wb'
        kwargs = {}
    else:
        access = 'wt'
        kwargs = {'newline': ''}
    # open file for writing
    csv_file = open(fname, access, **kwargs)

    # write to CSV
    try:
        writer = csv.writer(csv_file)
        header = ['Option Name', 'Developer', 'Contact', 'Address', 'WI-Fi', 'Year Built', 'Units', 'URL']
        writer.writerow(header)

        # parse current entire apartment list including pagination for all search urls
        write_parsed_to_csv(url, writer)

    finally:
        csv_file.close()

def write_parsed_to_csv(page_url, writer, i=0):

    '''
    Given the current page URL, extract the information from each apartment in the list
    '''

    if i>28:
        # Pagination does not exceed 28 pages
        return

    print ("Now getting apartments from: %s" % page_url)

    # read the current page
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}
    page = requests.get(page_url, headers=headers)
    print(page.status_code)
    if page.status_code != 200:
        return
    else:
        pass

    # soupify the current page
    soup = BeautifulSoup(page.content, 'html.parser')
    soup.prettify()
    # only look in this region
    soup = soup.find('div', class_='placardContainer')

    # append the current apartments to the list
    for item in soup.find_all('article', class_='placard'):
        url = ''
        contact = ''

        # Getting link for apartment
        if item.find('a', class_='placardTitle') is None: continue
        url = item.find('a', class_='placardTitle').get('href')

        # get the phone number and parse it to unicode
        obj = item.find('div', class_='phone')
        if obj is not None:
            contact = obj.getText().strip()

        # get the other fields to write to the CSV
        fields = parse_apartment_information(url)

        if 'Wi-Fi' in fields['features']:
            has_wifi = True
        else:
            has_wifi = False


        mask = re.compile('Built in \d{4}$')


        for f in fields['info']:

            if re.match(mask, f):
                year_built = int(f[-4:])
                break
            else:
                year_built = None

        mask = re.compile('\d{2,4} Units$')

        for f in fields['info']:
            if '/' in f:
                f = f.split('/')[0]
            else:pass
            if re.match(mask, f):
                units = int(f.split('Units')[0])
                break
            else:
                units = None



        # fill out the CSV file

        try:
            row = [fields['name'], fields['developer'], contact,
                   fields['address'], has_wifi,
                   year_built, units, url]
        except Exception as e:
            row = ['','','','','','','', '']


        # write the row
        writer.writerow(row)

    conf = configparser.ConfigParser()
    config_file = os.path.join(os.path.dirname(__file__), "config.ini")
    conf.read(config_file)

    # get the apartments.com search URL(s)
    apartments_url_config = conf.get('all', 'apartmentsURL')

    i += 1
    next_url = apartments_url_config.split('.com')[0] + '.com/{0}'.format(str(i)) + apartments_url_config.split('.com')[1]

    # recurse until the last page
    write_parsed_to_csv(next_url, writer, i)

def parse_apartment_information(url):

    '''
    For every apartment page, populate the required fields to be written to CSV
    '''

    # read the current page
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'}
    page = requests.get(url, headers=headers)

    # soupify the current page
    soup = BeautifulSoup(page.content, 'html.parser')
    soup.prettify()

    # the information we need to return as a dict
    fields = {}
    # get the name of the property
    get_property_name(soup, fields)
    # get the address of the property
    get_property_address(soup, fields)
    # get_property_size skipped
    # get_fees skipped
    # get_images skipped
    # get_description skipped
    get_developer(soup, fields)

    # only look in this section (other sections are for example for printing)
    soup = soup.find('section', class_='specGroup js-specGroup')

    # get_pet_policy skipped
    # get_parking_info skipped
    # get the amenities description
    # get_field_based_on_class(soup, 'amenities', 'featuresIcon', fields)
    # get the 'interior information'
    # get_field_based_on_class(soup, 'indoor', 'interiorIcon', fields)
    # get the 'outdoor information'
    # get_field_based_on_class(soup, 'outdoor', 'parksIcon', fields)
    # get the 'gym information'
    # get_field_based_on_class(soup, 'gym', 'fitnessIcon', fields)
    # get the 'kitchen information'
    # get_field_based_on_class(soup, 'kitchen', 'kitchenIcon', fields)
    # get the 'services information'
    # get_field_based_on_class(soup, 'services', 'servicesIcon', fields)
    # get the 'living space information'
    # get_field_based_on_class(soup, 'space', 'sofaIcon', fields)
    # get the lease length
    # get_field_based_on_class(soup, 'lease', 'leaseIcon', fields)
    # get the 'property information'
    get_features_and_info(soup, fields)

    # get the link to open in maps
    # fields['map'] = 'https://www.google.com/maps/dir/' \
    #                 + map_info['target_address'].replace(' ', '+') + '/' \
    #                 + fields['address'].replace(' ', '+') + '/data=!4m2!4m1!3e2'
    #
    # fields['distance'] = ''
    # fields['duration'] = ''
    # if map_info['use_google_maps']:
    #     # get the distance and duration to the target address using the Google API
    #     get_distance_duration(map_info, fields)

    return fields

def prettify_text(data):
    """Given a string, replace unicode chars and make it prettier"""

    # format it nicely: replace multiple spaces with just one
    data = re.sub(' +', ' ', data)
    # format it nicely: replace multiple new lines with just one
    data = re.sub('(\r?\n *)+', '\n', data)
    # format it nicely: replace bullet with *
    data = re.sub(u'\u2022', '* ', data)
    # format it nicely: replace registered symbol with (R)
    data = re.sub(u'\xae', ' (R) ', data)
    # format it nicely: remove trailing spaces
    data = data.strip()
    # format it nicely: encode it, removing special symbols
    data = data.encode('utf8', 'ignore')

    return str(data).encode('utf-8')

def get_features_and_info(soup, fields):
    """Given a beautifulSoup parsed page, extract the features and property information"""

    fields['features'] = ''
    fields['info'] = ''

    if soup is None: return

    obj = soup.find('i', class_='propertyIcon')

    if obj is not None:
        for obj in soup.find_all('i', class_='propertyIcon'):
            data = obj.parent.findNext('ul').getText()
            data = prettify_text(data)

            if obj.parent.findNext('h3').getText().strip() == 'Features':
                # format it nicely: remove trailing spaces
                data = data.decode("utf-8")[4:-1].split('\\n* ')
                fields['features'] = data
            if obj.parent.findNext('h3').getText() == 'Property Information':
                # format it nicely: remove trailing spaces\
                data = data.decode("utf-8")[4:-1].split('\\n* ')
                fields['info'] = data

def get_property_name(soup, fields):

    '''
    Given a beautifulSoup parsed page, extract the name of the property
    '''

    fields['name'] = ''

    # get the name of the property
    obj = soup.find('h1', class_='propertyName')
    if obj is not None:
        name = obj.getText()
        name = prettify_text(name)
        name = name.decode("utf-8")[2:-1]
        fields['name'] = name

def find_addr(script, tag):
    """Given a script and a tag, use python find to find the text after tag"""

    tag = tag + ": \'"
    start = script.find(tag)+len(tag)
    end = script.find("\',", start)
    return script[start : end]

def get_property_address(soup, fields):
    """Given a beautifulSoup parsed page, extract the full address of the property"""

    address = ""

    # They changed how this works so I need to grab the script
    script = soup.findAll('script', type='text/javascript')[2].text

    # The address is everything in quotes after listingAddress
    address = find_addr(script, "listingAddress")

    # City
    address += ", " + find_addr(script, "listingCity")

    # State
    address += ", " + find_addr(script, "listingState")

    # Zip Code
    address += " " + find_addr(script, "listingZip")

    fields['address'] = address

def get_developer(soup, fields):
    """Get the images of the apartment"""

    fields['developer'] = ''

    if soup is None: return

    soup = soup.find('div', {'class': 'logoColumnContainer'})
    if soup is not None:
        for img in soup.find_all('img'):
            fields['developer'] = img['alt']

def main():
    '''
    Read from the config file and get the Google maps info optionally
    '''

    conf = configparser.ConfigParser()
    config_file = os.path.join(os.path.dirname(__file__), "config.ini")
    conf.read(config_file)

    # get the apartments.com search URL(s)
    apartments_url_config = conf.get('all', 'apartmentsURL')
    url = apartments_url_config
    print(url)

    # get the name of the output file
    fname = conf.get('all', 'fname') + '.csv'

    create_csv(url, fname)

def get_frame(csv_fname):

    frame = pd.read_csv('output.csv')
    frame.drop_duplicates(keep="first", inplace=True)

    # Getting Lats and Lons

    for inum, row in frame.iterrows():
        
        geolocator = Nominatim()
        try:
            location = geolocator.geocode(row['Address'], timeout=None)
            lat = location.latitude
            lon = location.longitude
            frame.set_value(inum, 'Lat', lat)
            frame.set_value(inum, 'Lon', lon)
        except Exception as e:
            print(e)

    frame.dropna(axis=0, inplace=True)
    frame.sort_values('Units', axis=0, ascending=False, inplace=True)
    frame.reset_index(drop=True, inplace=True)


    writer = pd.ExcelWriter('apartments.xlsx')
    frame.to_excel(writer, 'Apartments')
    writer.save()

    return frame

def find_ohio_coop(long, lat, data):

    point = Point(long, lat)

    for inum, row in data.iterrows():
        if shape(row['geometry']).contains(point):

            company = row['CompanySho']
            break
        else:

            company = False

    if not company:
        company = ''

    return company

def get_providers():

    curr_dir = os.getcwd()
    shapefiles_dir = os.path.join(curr_dir, 'shapefiles')

    os.chdir(shapefiles_dir)

    fp = "Current_Boundary.shp"
    fc = fiona.open(fp)

    data = gpd.read_file(fp)
    os.chdir(curr_dir)

    data.to_crs({"init": "epsg:4326"}, inplace=True)

    frame = pd.read_excel('apartments.xlsx')

    for inum, row in frame.iterrows():

        lat = frame.iloc[inum]['Lat']
        long = frame.iloc[inum]['Lon']

        provider = find_ohio_coop(long, lat, data)

        frame.set_value(inum, 'Provider', provider)

    writer = pd.ExcelWriter('apartments.xlsx')
    frame.to_excel(writer, 'Apartments')
    writer.save()


if __name__ == '__main__':

    main()

    get_frame('output.csv')

    get_providers()
