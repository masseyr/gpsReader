#! /usr/bin/python
from functools import wraps
from gps import *
import time
import sys
import os
import signal
import json

"""
Python script to read GPS coordinates and write to stdout
"""


class TimeOutError(Exception):
    """
    Error class for use in returning fields that may be in error.
    """
    status_code = 408

    def __init__(self,
                 seconds=10,
                 error="Request timed out",                 
                 status_code=status_code,
                 headers=None):
        """
        :param error: name of error
        :param status_code: the http status code
        :param headers: any applicable headers
        :return:
        """
        self.description = "Request timed out at {} seconds".format(seconds)
        self.status_code = status_code
        self.headers = headers
        self.error = error
    
    def __repr__(self):
        return self.description

    def __str__(self):
        return self.description


def timeout(seconds=10):
    """
    wrapper to end requests that time out
    """
    def decorator(func):

        def handler(signum, frame):
            raise TimeOutError(seconds=seconds)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator


def take_note(gps_dict,
              host='127.0.0.1',
              port='2947'):
    """
    Function to read from stored coords if the gps read fails

    """
    last_reading_file = '/tmp/gpscoords-{}-{}'.format(host,
                                                      port)

    if (gps_dict is None) or (gps_dict['lat'] == 'Nofix'):
        if os.path.isfile(last_reading_file):
            with open(last_reading_file, 'r') as gpsf:
                fileline = gpsf.readlines()
                gps_str = fileline[0].strip()

    else:
        gps_str = '{} {} {} {}'.format(gps_dict['lat'],
                                       gps_dict['lon'],
                                       gps_dict['alt'],
                                       gps_dict['time'])
        with open(last_reading_file, 'w') as gpsf:
            gpsf.write(gps_str)

    sys.stdout.write(gps_str + '\n')


@timeout(15)
def get_gps(host='127.0.0.1', 
            port='2947'):
    """
    Function to get GPS coordinates from a working gpsd reading a GPS device
    format: latitide longitude altitude(m) time(UTC)
    This function will time out in 15 seconds
    """    

    gpsd = gps(host=host,
               port=port,
               mode=WATCH_ENABLE|WATCH_NEWSTYLE)

    while True:
        report = gpsd.next()
        if report['class'] == 'TPV':
            return {'lat': getattr(report,'lat','Nofix'),
                    'lon': getattr(report,'lon','Nofix'),
                    'alt': getattr(report,'alt','Nofix'),
                    'time': getattr(report,'time','Nofix')}


if __name__ == '__main__':

    host = '127.0.0.1'
    port = '2947'

    if len(sys.argv) == 1:
        pass
    if len(sys.argv) == 2:
        script, host = sys.argv
    elif len(sys.argv) == 3:
        script, host, port = sys.argv
    elif len(sys.argv) > 3:
        sys.stdout.write("Ignoring extra arguments\n")
        script, host, port = sys.argv[0:3]

    try:
        gps_dict = get_gps(host=host, port=port)
        take_note(gps_dict, host=host, port=port)
    except Exception as e:
        sys.stdout.write(e.args[0])
