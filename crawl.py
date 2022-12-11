#!/usr/bin/env python3

import re
import argparse
import urllib.request
from lxml import etree
from io import StringIO
from time import time
from datetime import date, datetime, timedelta
from random import getrandbits
from collections import defaultdict


RESPONSE_RE = 'jQuery\d+_\d+\({"contents":"(.*)"\}\);'
# IDs are for all 1 hour time slots only
#TYPE_ID = {
#    'weekday_5-14': 14,
#    'weekday_14-18': 5, 
#    'weekday_18-22': 18, 
#    'weekday_22-0': 1128,
#    'weekend_5-8': 35,
#    'weekend_8-19': 25,
#    'weekend_19-0': 29,
#}

URL = 'https://widgets.mindbodyonline.com/widgets/appointments/8f25324d818/results.json?callback=%3F&callback=jQuery1810{random}_{timestamp}&utf8=%E2%9C%93&options%5Bsession_type_ids%5D={type_id}&options%5Bstaff_ids%5D%5B%5D=&options%5Bstart_date%5D={start_date}&options%5Bend_date%5D={end_date}&_={timestamp}'


def valid_time(t):
  try:
    if ':' not in t:
      return datetime.strptime(t, '%H').time()
    else:
      return datetime.strptime(t, '%H:%M').time()
  except ValueError:
    raise argparse.ArgumentTypeError('not a valid time: {!r}'.format(t))
    
def build_url(start_date, end_date, type_id):
  return URL.format(random=getrandbits(64),
                    start_date=start_date.strftime('%Y-%m-%d'),
                    end_date=end_date.strftime('%Y-%m-%d'),
                    type_id=type_id,#TYPE_ID[type_id],
                    timestamp=get_timestamp())

def get_timestamp():
  return int(time() * 1000) # timestamp is milliseconds

def fetch(url):
  req = urllib.request.Request(url)
  req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/105.0.0.0 Safari/537.36')
  #with open('response', 'r') as f:
  with urllib.request.urlopen(req) as f:
    m = re.match(RESPONSE_RE, f.read().decode('utf-8'))
    if m == None:
      raise Exception('regex failed')

    response = m.group(1).replace('\\u003c', '<') \
                         .replace('\\u003e', '>') \
                         .replace('\\n', '\n') \
                         .replace('\\"', '"')
    #print(response)
    return response

def parse(html):
  tree = etree.parse(StringIO(html))
  result = defaultdict(list)

  for day in tree.xpath('//div[@class="appointment-date-block"]'):
    # XXX not sure what it'll look like if grabbing a week, but a day in the week is empty
    if day.xpath('.//p[@id="no_appointments_message"]'):
      print(day.text + ' has no appointments')
      return {}

    date = datetime.strptime(day.xpath('.//h1')[0].text, '%A %B %d, %Y')

    if date.date() < earliest_date.date() and date.date() > latest_date.date():
      raise Exception('Date Error. Format probably changed.')
    #print(day.xpath('.//h1')[0].text)

    courts = day.xpath('.//div[@class="healcode-trainer"]')
    for court in courts:
      name = court.xpath('.//div/a')[0].text
      #print('\t' + name)
      for t in court.xpath('.//span/a'):
        #print('\t' + t.text)
        t = datetime.strptime(
            '{}-{}-{} {}'.format(date.year, date.month, date.day, t.text.strip()), 
            '%Y-%m-%d %I:%M %p')
        #print(t.time() >= earliest_date.time() and t.time() <= latest_date.time())
        if t.time() >= earliest_date.time() and t.time() <= latest_date.time():
          #print('adding to result{}')
          result['{}, {}'.format(date.strftime('%B %d, %Y'), name)].append(t)

  return result


parser = argparse.ArgumentParser(
                    prog = 'crawl.py',
                    description = 'Crawl McCarren Tennis site and find open slots. Might take a while for a large date range.',
                    formatter_class=argparse.RawTextHelpFormatter)
parser.add_argument('--ed', metavar='EARLIEST_DATE', type=date.fromisoformat, required=True, help='Earliest date to play. Format YYYY-MM-DD.')
parser.add_argument('--ld', metavar='LATEST_DATE', type=date.fromisoformat, required=True, help='Latest date to play. Format YYYY-MM-DD.')
parser.add_argument('--et', metavar='EARLIEST_TIME', type=valid_time, required=True, help='Earliest start time.')
parser.add_argument('--lt', metavar='LATEST_TIME', type=valid_time, required=True, help='Latest start time')
parser.add_argument('--id', type=int, default=1128, help='''Use associated ID for the desired time slot you are looking for. IDs are for all 1 hour time slots only. Default 1128.
    weekday 5-14  :   14
    weekday 14-18 :    5
    weekday 18-22 :   18 
    weekday 22-0  : 1128
    weekend 5-8   :   35
    weekend 8-19  :   25
    weekend 19-0  :   29''')
args = parser.parse_args()

# date & time are indepdendent but just putting in same date var for convenience
earliest_date = datetime.strptime('{} {}'.format(args.ed, args.et), 
                                  '%Y-%m-%d %H:%M:%S')
latest_date = datetime.strptime('{} {}'.format(args.ld, args.lt), 
                                '%Y-%m-%d %H:%M:%S')
if latest_date.time().hour == 0:
  latest_date.replace(hour=23, minute=59)
if earliest_date.date() > latest_date.date():
  raise argparse.ArgumentTypeError(
      'earliest date must before latest date: {!r} vs {!r}'.format(
        earliest_date.date(), latest_date.date()))
if earliest_date.time() > latest_date.time():
  raise argparse.ArgumentTypeError(
      'earliest time must before latest time: {!r} vs {!r}'.format(
        earliest_date.time(), latest_date.time()))

print('Finding slots between\n{} - {}\nStarting between {}-{}\n'.format(
                                        earliest_date.strftime('%b %d, %Y'),
                                        latest_date.strftime('%b %d, %Y'),
                                        earliest_date.strftime('%H:%M'),
                                        latest_date.strftime('%H:%M')))

url = build_url(earliest_date, latest_date, args.id)
response = fetch(url)
a = parse(response)
for k in a.keys():
  print(k)
  for t in a[k]:
    print(t.strftime('%H:%M'))
