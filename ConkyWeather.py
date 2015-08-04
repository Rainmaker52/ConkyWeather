#!/usr/bin/python3

'''
ConkyWeather will provide several useful Conky functions.
'''

'''
Helper functions
'''
def getexternalip():
    import requests
    import json

    dprint('Getting IP information')
    # Get external IP
    try:
        r = requests.get('http://jsonip.com', timeout=10)
    except requests.exceptions.Timeout:
        raise NoInternet
    ip = json.loads(r.text)['ip']
    return ip

def getlocation(ip):
    import requests
    import json

    dprint('Getting location')
    try:
        r = requests.get('http://freegeoip.net/json/{}'.format(ip), timeout=10).text
    except requests.exceptions.Timeout as e:
        dprint('Could not get location information'.format(e))
        if progargs.debug:
            dprint('Filling information with bogus information')
            r = '{"ip":"77.242.120.51","country_code":"NL","country_name":"Netherlands","region_code":"ZH","region_name":"South Holland","city":"Boskoop","zip_code":"2771","time_zone":"Europe/Amsterdam","latitude":52.075,"longitude":4.656,"metro_code":0}'
            return r
        else:
            r = '{}'
            raise NoInternet

    return json.loads(r)

def doyahooquery(query, url='https://query.yahooapis.com/v1/public/yql?format=json&q='):
    import requests
    import json
    from urllib.parse import quote

    u = '{}{}'.format(url, quote(query))
    dprint('Getting {}'.format(u))

    try:
        r = requests.get(u, timeout=10)
    except requests.exceptions.Timeout:
        raise NoInternet

    dprint('Returning {}'.format(r.text))
    return json.loads(r.text)

def getwoeid(zip, country):
    dprint('Getting fresh WOE ID')
    q = "SELECT * FROM geo.places WHERE text='{}' AND country='{}'".format(zip, country)
    return doyahooquery(q)

def getweather(woeid, day=0):
    # u = 'http://weather.yahooapis.com/forecastrss?u=c&w='
    q = "SELECT * FROM weather.forecast WHERE u='c' AND woeid = {}".format(woeid)
    dprint('Getting weather for WOEID {}'.format(woeid))

    return doyahooquery(q)

def link_image(imagenum, conditioncode, local):
    '''
    Link the appropiate image (stolen from the Google-Now Conky config). Use symlinks instead of copy because
    that's better

    :param imagenum: 0 for current conditions. 1 for 1 day in the future. 2 for 2 days in the future. etc.
    :param conditioncode: Yahoo weather API condition code https://developer.yahoo.com/weather/documentation.html#codes
    :param local: Whether image is for "local" weather (0) or "home" (1)
    :return: True (success) or False (unsucessful)
    '''
    from os import readlink, symlink, path, unlink

    try:
        filename = 'weather{}-{}.png'.format(imagenum, local)

        # Check whether symlink already exists and points to the correct image
        dprint('Checking for symlink for image type {}. Condition {}. IsLocal? {}. Filename {}'.format(
            imagenum, conditioncode, local, filename))
        t = readlink('{}/{}'.format(temppath, filename))
        dprint('Link {} is currently pointing to {}'.format(filename, t))
        if not path.split(t)[-1] == '{}.png'.format(conditioncode):
            raise Exception

        # Already exists and points to the correct image. We're done.
    except:
        # Does not exist. Or, points to the wrong image. Unlink current one if it exists
        try:
            unlink('{}/weather{}-{}.png'.format(temppath, imagenum, local))
        except: pass

        symlink('{}/{}.png'.format(imagepath, conditioncode), '{}/weather{}-{}.png'.format(temppath, imagenum, local))

def check_internet():
    import requests
    try:
        response = requests.get('http://google.nl',timeout=1)
        if response.status_code != 200:
            dprint('Got error {} when checking for internet connectivity'.format(response.status_code))
            raise NoInternet

        return True
    except:
        raise NoInternet

def savecacheline(cachetype, cachecontent):
    from os import mkdir, path, unlink

    dprint('Saving cache {}. Content: {}'.format(cachetype, cachecontent))

    # Does the temp path exist?
    try:
        if not path.exists(temppath):
            dprint('Temp path does not yet exist. Creating...')
            mkdir(temppath)
    # Directory could not be created...
    except:
        raise

    # Get lock on cache
    if path.isfile('{}/cache.lock'.format(temppath)):
        # Lock file exists! We don't have lock, and must assume a different thread is currently building it
        # Exit this instance, and hope thing go better on the next run.
        raise CacheLocked

    c = list()

    open('{}/cache.lock'.format(temppath), 'a').close()
    try:
        with open('{}/cache.json'.format(temppath), 'r') as f:
            try:
                c = f.readlines()
            except:
                dprint('Could not read from cachefile.')
            finally:
                f.close()
    except FileNotFoundError: pass  # Ignore when the file does not already exist

    with open('{}/cache.json'.format(temppath), 'w') as f:
        try:
            l = list()

            try:
                for i in range(3):
                    t = c[i]
            except IndexError:
                # File is empty
                for i in range(3):
                    c.append('')

            # Determine to write to which line
            if cachetype == 'LocationInfo':
                l.append(cachecontent)
                l.append(c[1].strip('\n'))
                l.append(c[2].strip('\n'))
            elif cachetype == 'LocalWeather':
                l.append(c[0].strip('\n'))
                l.append(cachecontent)
                l.append(c[2].strip('\n'))
            elif cachetype == 'HomeWeather':
                l.append(c[0].strip('\n'))
                l.append(c[1].strip('\n'))
                l.append(cachecontent)
            else:
                raise AssertionError

            for line in l:
                f.write('{}\n'.format(line))

        except:
            dprint('Could not write content to cachefile.')
            raise
        finally:
            try:
                f.close()
                unlink('{}/cache.lock'.format(temppath))
            except FileNotFoundError: pass

        # Restart program to re-read cache
        restart()

def restart():
    import os
    import sys

    dprint('Restarting program. Arguments {}'.format(sys.argv))
    python = sys.executable
    os.execl(python, python, * sys.argv)

def readcache():
    c = list()
    try:
        with open('{}/cache.json'.format(temppath), 'r') as f:
            c = f.readlines()
    except FileNotFoundError:
        # Set this to build from a clean cache.
        raise UnreadableCache

    if(len(c)) != 3:
        raise UnreadableCache

    return c

def to24hourtime(hourtime):
    from time import strftime, strptime
    t = strptime(hourtime, '%I:%M %p')
    n = strftime('%H:%M', t)
    return n

def dprint(*args, **kwargs):
    if progargs.debug:
        print(*args, **kwargs)

'''
Class definitions
'''

'''
Exception classes
'''
class NoInternet(Exception):
    def __repr__(self):
        return 'Internet connectivity could not be verified'

class CacheExpired(Exception):
    def __repr__(self):
        return 'The cache for {} has expired'.format(self.__name__)

    def __init__(self, modulename):
        self.modulename = modulename
        dprint('Cache expired for {}'.format(self.modulename))


class UnreadableCache(Exception):
    def __repr__(self):
        return 'The cache for {} could not be read'.format(self.__name__)

    def __init__(self):
        dprint('Cache unreadable')

class CacheLocked(Exception):
    def __repr__(self):
        return 'The cache is locked'

class InvalidArgumentsSupplied(Exception):
    def __repr__(self):
        return 'Invalid combination of arguments supplied'

'''
Data classes
'''
class JSONObject(object):
    def __init__(self, cachecontent):
        from time import time

        self.cacheexpires = int(time() + 60)  # Set default expiration at 1 minute

        if cachecontent is not None:
            self.load_json(cachecontent)

    def as_json(self):
        from json import dumps

        dprint('Passing object for {}...'.format(self.__class__.__name__))

        try:
            r = dumps(self.__dict__)
            return r
        except:
            raise Exception

    def load_json(self, cachecontent):
        from json import loads
        from time import time

        dprint('Loading cache for {}...'.format(self.__class__.__name__))

        # Load the cache from the content
        try:
            r = loads(cachecontent)
            self.__dict__ = r

            if r['cacheexpires'] <= int(time()):
                dprint('Cache has expired. Time now: {}. Time expired: {}!'.format(time(), r['cacheexpires']))
                raise Exception
            else:
                return True
        except:
            # Cache file could not be loaded? Recreate cache.
            raise CacheExpired(self.__class__.__name__)

    def createcache(self):
        # Overwritten by child classes
        pass


class LocationInfo(JSONObject):
    def __init__(self, cachecontent=None):
        # Global info (where are we)
        self.ip = None
        self.city = None
        self.country = None
        self.zipcode = None
        self.woeid = 0

        super(LocationInfo, self).__init__(cachecontent)

    def createcache(self):
        from time import time

        self.ip = getexternalip()

        r = getlocation(self.ip)
        self.country = r['country_name']
        self.city = r['city']
        self.zipcode = r['zip_code']

        woeinfo = getwoeid(self.zipcode, self.country)
        self.woeid = woeinfo['query']['results']['place']['woeid']

        dprint('WOEID now set for locationinfo to {}'.format(self.woeid))

        # Fields retrieved. Set timeout for 1 hour
        self.cacheexpires = int(time() + 3600)

        return self.as_json()


class WeatherInfo(JSONObject):
    '''
    Holds information for 1 day of wheather
    '''
    def __init__(self, cachecontent=None):
        # Actual weather info
        self.woeid = qwoeid

        super(WeatherInfo, self).__init__(cachecontent)

    def createcache(self):
        from time import time
        r = getweather(self.woeid)

        try:
            # Store 3 variables for each day
            for i in range(5):
                low = r['query']['results']['channel']['item']['forecast'][i]['low']
                high = r['query']['results']['channel']['item']['forecast'][i]['high']
                self.__dict__['temperature{}'.format(i)] = '{}-{}°C'.format(low, high)
                self.__dict__['condition{}'.format(i)] = r['query']['results']['channel']['item']['forecast'][i]['code']
                self.__dict__['day{}'.format(i)] = r['query']['results']['channel']['item']['forecast'][i]['day']

            # Store wind information
            self.__dict__['winddirection'] = r['query']['results']['channel']['wind']['direction']
            self.__dict__['windspeed'] = r['query']['results']['channel']['wind']['speed']

            # Store sunrise information
            self.__dict__['sunrise'] = r['query']['results']['channel']['astronomy']['sunrise']
            self.__dict__['sunset'] = r['query']['results']['channel']['astronomy']['sunset']
        except KeyError:
            pass

        self.cacheexpires = int(time()) + 3600

        return self.as_json()

class LocalWeather(WeatherInfo):
    pass

class HomeWeather(WeatherInfo):
    pass

# Main program
import argparse

parser = argparse.ArgumentParser(description='Conky script to get weather information and more.')

group = parser.add_argument_group('Information', 'Commands which return information without requiring extra arguments')
group.add_argument('--externalip', action='store_true', help='get the external IP address')
group.add_argument('--location', action='store_true', help='get the location, based on the external IP address.'
                    'This will depict the closest weather station')
group.add_argument('--woeid', action='store_true', help='get the Yahoo WOEID.')

group = parser.add_argument_group('Location switches', 'Specifiy one of the below to indicate for which location to get information')
group.add_argument('--home', action='store_true', help='Display weather info for home location. Also specify --homewoe')
group.add_argument('--local', action='store_true', help='Display weather info for local location, based on IP')

group = parser.add_argument_group('Information per location', 'Specifiy the attribute which to return. --home or --local should be specified')
group.add_argument('--dow', action='store_true', help='get the day of week for a given --day object. This DOES need --local or --home')
group.add_argument('--sunset', action='store_true', help='Return sunset')
group.add_argument('--sunrise', action='store_true', help='Return sunrise')
group.add_argument('--windspeed', action='store_true', help='Return wind direction')
group.add_argument('--winddirection', action='store_true', help='Return wind direction')

group = parser.add_argument_group('Program flow', 'These switches influence exection of the program')
group.add_argument('--debug', action='store_true', help='Enable debugging. Note that the extra output makes it unsuitable for use with Conky.')

group = parser.add_argument_group('Information per day and location', 'Specify one of these attributes to return information. '
            'Both --home (and homewoe) OR --local should be specified AND --day should be specified')
group.add_argument('--temperature', action='store_true', help='Return temperature')

group = parser.add_argument_group('Arguments', 'Specify this information together with the options above.')
group.add_argument('--homewoe', help='Specify the WOEID for home. Only useful when combined with --home')
group.add_argument('--dayname', action='store_true', help='Return day of the week (Mon, Tue...). Specify with --day')
group.add_argument('--day', help='Return attributes for <day> (0=today)')

progargs = parser.parse_args()

from os.path import expanduser

temppath = '/tmp/conky-weather'
imagepath = '{}/.conky/images'.format(expanduser("~"))
homewoeid = progargs.homewoe
qwoeid = None
#homewoe = '727232'  # Amsterdam (testing)

# Try open the cache file
# Cache file layout:
#   line 1: Geo info. Passed to LocationInfo()
#   line 2: Weatherinfo object - Local wather
#   line 3: Weatherinfo object - Home weather

try:
    c = readcache()
    l = None

    # We'll need location info for almost all cases
    try:
        l = LocationInfo(c[0]) if not progargs.home else None
    except IndexError:
        raise UnreadableCache

    dprint('After location cache')

    # Detemine what we must return
    # Location info only
    if progargs.externalip:
        print(l.ip)
    elif progargs.location:
        print('{}, {}'.format(l.city, l.country))
    elif progargs.woeid:
        print(l.woeid)
    # Weather information for the current location
    elif progargs.local:
        dprint('Requested local weather (current location). WOEID {}'.format(l.woeid))
        # Store the WOEID in a global variable. This will allow us to pick it up during exceptions, while
        # still having a generic exception handler.
        try:
            qwoeid = l.woeid
            w = LocalWeather(c[1])
        except (IndexError, AttributeError) as e:
            dprint('Unable to assign "local" WOEID or read local cache. Got {}. Error: {}'.format(l.woeid, e))
            raise UnreadableCache

        try:
            # Update the images
            for i in range(5):
                link_image(i, w.__getattribute__('condition{}'.format(i)), "0")

            # Return requested attribute
            if progargs.temperature:
                print(w.__getattribute__('temperature{}'.format(progargs.day)))
            elif progargs.windspeed:
                print(w.__getattribute__('windspeed'))
            elif progargs.winddirection:
                print(w.__getattribute__('winddirection'))
            elif progargs.sunset:
                r = w.__getattribute__('sunset')
                print(to24hourtime(r))
            elif progargs.sunrise:
                r = w.__getattribute__('sunrise')
                print(to24hourtime(r))
            elif progargs.dow:
                print(w.__getattribute__('day{}'.format(progargs.day)))

        except AttributeError as e:
            dprint('Could not get attribute: {}'.format(e))

    elif progargs.home:
        if homewoeid is None:
            raise InvalidArgumentsSupplied

        dprint('Requested home weather. WOEID {}'.format(homewoeid))
        try:
            qwoeid = homewoeid
            w = HomeWeather(c[2])
        except (IndexError, AttributeError) as e:
            dprint('Unable to assign "home" WOEID or read home cache. Got {}. Error: {}'.format(l.woeid, e))
            raise CacheExpired('HomeWeather')

        try:
            # Update the images
            for i in range(5):
                link_image(i, w.__getattribute__('condition{}'.format(i)), "1")

            # Return requested attribute
            if progargs.temperature:
                print(w.__getattribute__('temperature{}'.format(progargs.day)))
            elif progargs.windspeed:
                print(w.__getattribute__('windspeed'))
            elif progargs.winddirection:
                print(w.__getattribute__('winddirection'))
            elif progargs.sunset:
                r = w.__getattribute__('sunset')
                print(to24hourtime(r))
            elif progargs.sunrise:
                r = w.__getattribute__('sunrise')
                print(to24hourtime(r))
            elif progargs.dow:
                print(w.__getattribute__('day{}'.format(progargs.day)))

        except AttributeError as e:
            dprint('Could not get attribute: {}'.format(e))

except UnreadableCache as err:
    from os import path

    # All caches need to be rebuilt
    dprint('No cache found. Rebuilding')

    check_internet()

    # Check whether we're going to need Location (all situations except for Home wather information).
    if progargs.home:
        qwoeid = homewoeid
        c = HomeWeather().createcache()
        savecacheline('HomeWeather', c)
    else:
        c = LocationInfo().createcache()
        savecacheline('LocationInfo', c)

    # Re-read the cache
    restart()

except CacheExpired as err:
    from os import path

    # Only a certain cache needs to be rebuilt.
    dprint('Rebuilding cache for {}'.format(err.modulename))

    check_internet()

    cachetype = err.modulename
    cachecontent = globals()[err.modulename]().createcache()

    savecacheline(cachetype, cachecontent)

except CacheLocked as err:
    dprint('The cache is locked. Not contuning')

except NoInternet:
    # We have to do some cache actions, but have no internet.
    dprint('No internet connetivity seems to be present.')

    # We have no (valid) cache, and we could not build it. This is a fatal error.
    # Replace all icons by "unknown" (3200)
    for i in range(5):
        link_image(i, 3200, 0)
        link_image(i, 3200, 1)

    # Unlink cache file, if it exists. Retry always on next run
    try:
        unlink('{}/cache.json'.format(temppath))
    except FileNotFoundError: pass

except InvalidArgumentsSupplied:
    import os
    import sys

    print('You have supplied an invalid combination of arguments.')

    python = sys.executable
    os.execl(python, python, sys.argv[0], '--help')

finally:
    # Remove lockfile. Ensure that it'll be gone on next run
    try:
        from os import unlink

        unlink('{}/cache.lock'.format(temppath))
    # But don't error out if it doesn't exist
    except FileNotFoundError: pass

