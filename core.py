import os
from slackclient import SlackClient

SLACK_TOKEN = os.environ.get('SLACK_TOKEN', None)
SCAN_BLOCKS = os.environ.get('SCAN_BLOCKS', None)
TOTAL_WORKER_LIFETIME = os.environ.get('TOTAL_WORKER_LIFETIME', None)
RPC_ID = int(os.environ.get('RPC_ID', None))
DEBUG = bool(os.environ.get('DEBUG_STATE', None))

slack_client = SlackClient(SLACK_TOKEN)
        
import requests
import re
import struct
import json
import argparse
import pokemon_pb2
import time

import csv

from google.protobuf.internal import encoder

from datetime import datetime
from time import sleep
from geopy.geocoders import GoogleV3
from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
from s2sphere import *

API_URL = 'https://pgorelease.nianticlabs.com/plfe/rpc'
LOGIN_URL = 'https://sso.pokemon.com/sso/login?service=https%3A%2F%2Fsso.pokemon.com%2Fsso%2Foauth2.0%2FcallbackAuthorize'
LOGIN_OAUTH = 'https://sso.pokemon.com/sso/oauth2.0/accessToken'

SESSION = requests.session()
SESSION.headers.update({'User-Agent': 'Niantic App'})
SESSION.verify = False 

POKEMONS = json.load(open('pokemon.json'))

def send_message(channel_id, message):
    slack_client.api_call(
        "chat.postMessage",
        channel=channel_id,
        text=message,
        username='Pokemon-Alert',
        icon_emoji=':fire:'
    )

def encode(cellid):
    output = []
    encoder._VarintEncoder()(output.append, cellid)
    return ''.join(output)

def getNeighbors(float_lat,float_long):
    origin = CellId.from_lat_lng(LatLng.from_degrees(float_lat, float_long)).parent(15)
    walk = [origin.id()]
    # 10 before and 10 after
    next = origin.next()
    prev = origin.prev()
    for i in range(10):
        walk.append(prev.id())
        walk.append(next.id())
        next = next.next()
        prev = prev.prev()
    return walk

def f2i(input_float):
  return struct.unpack('<Q', struct.pack('<d', input_float))[0]

def f2h(input_float):
  return hex(struct.unpack('<Q', struct.pack('<d', input_float))[0])

def h2f(input_hex):
  return struct.unpack('<d', struct.pack('<Q', int(input_hex,16)))[0]

def get_location(location_name):
    geolocator = GoogleV3()
    loc = geolocator.geocode(location_name)

    print('[!] Your given location: {}'.format(loc.address.encode('utf-8')))
    print('[!] lat/long/alt: {} {} {}'.format(loc.latitude, loc.longitude, loc.altitude))
    
    return (loc.latitude,loc.longitude,loc.altitude)


def api_req(api_endpoint, access_token, coords_lat, coords_long, coords_alt, *mehs, **kw):
    try:
        p_req = pokemon_pb2.RequestEnvelop()
        p_req.rpc_id = RPC_ID

        p_req.unknown1 = 2

        p_req.latitude = coords_lat
        p_req.longitude = coords_long
        p_req.altitude = coords_alt

        p_req.unknown12 = 989

        if 'useauth' not in kw or not kw['useauth']:
            p_req.auth.provider = 'ptc'
            p_req.auth.token.contents = access_token
            p_req.auth.token.unknown13 = 14
        else:
            p_req.unknown11.unknown71 = kw['useauth'].unknown71
            p_req.unknown11.unknown72 = kw['useauth'].unknown72
            p_req.unknown11.unknown73 = kw['useauth'].unknown73

        for meh in mehs:
            p_req.MergeFrom(meh)

        protobuf = p_req.SerializeToString()

        r = SESSION.post(api_endpoint, data=protobuf, verify=False)

        p_ret = pokemon_pb2.ResponseEnvelop()
        p_ret.ParseFromString(r.content)

        if DEBUG:
            print("REQUEST:")
            print(p_req)
            print("Response:")
            print(p_ret)
            print("\n\n")

        print("Sleeping for 2 seconds to get around rate-limit.")
        time.sleep(2)
        return p_ret
    except Exception as e:
        if DEBUG:
            print(e)
        raise
        return None

def get_profile(access_token, api, coords_lat, coords_long, useauth, *reqq):
    req = pokemon_pb2.RequestEnvelop()

    req1 = req.requests.add()
    req1.type = 2
    if len(reqq) >= 1:
        req1.MergeFrom(reqq[0])

    req2 = req.requests.add()
    req2.type = 126
    if len(reqq) >= 2:
        req2.MergeFrom(reqq[1])

    req3 = req.requests.add()
    req3.type = 4
    if len(reqq) >= 3:
        req3.MergeFrom(reqq[2])

    req4 = req.requests.add()
    req4.type = 129
    if len(reqq) >= 4:
        req4.MergeFrom(reqq[3])

    req5 = req.requests.add()
    req5.type = 5
    if len(reqq) >= 5:
        req5.MergeFrom(reqq[4])

    return api_req(api, access_token, coords_lat, coords_long, 0, req, useauth = useauth)

def get_api_endpoint(access_token, coords_lat, coords_long, api = API_URL):
    p_ret = get_profile(access_token, api, coords_lat, coords_long, None)
    try:
        return ('https://%s/rpc' % p_ret.api_url)
    except:
        return None


def login_ptc(username, password):
    
    print('[!] login for: {}'.format(username))
    head = {'User-Agent': 'niantic'}
    r = SESSION.get(LOGIN_URL, headers=head)
    if DEBUG:
        print(r.content)
    jdata = json.loads(r.content)
    data = {
        'lt': jdata['lt'],
        'execution': jdata['execution'],
        '_eventId': 'submit',
        'username': username,
        'password': password,
    }
    r1 = SESSION.post(LOGIN_URL, data=data, headers=head)
    ticket = None
    try:
        ticket = re.sub('.*ticket=', '', r1.history[0].headers['Location'])
    except Exception as e:
        if DEBUG:
            print(r1.json()['errors'][0])
        return None

    data1 = {
        'client_id': 'mobile-app_pokemon-go',
        'redirect_uri': 'https://www.nianticlabs.com/pokemongo/error',
        'client_secret': 'w8ScCUXJQc6kXKw8FiOhd8Fixzht18Dq3PEVkUCP5ZPxtgyWsbTvWHFLm2wNY0JR',
        'grant_type': 'refresh_token',
        'code': ticket,
    }
    r2 = SESSION.post(LOGIN_OAUTH, data=data1)
    access_token = re.sub('&expires.*', '', r2.content)
    access_token = re.sub('.*access_token=', '', access_token)
        
    return access_token

def heartbeat(api_endpoint, access_token, response, float_lat, float_long):
    try:
        m4 = pokemon_pb2.RequestEnvelop.Requests()
        m = pokemon_pb2.RequestEnvelop.MessageSingleInt()
        m.f1 = int(time.time() * 1000)
        m4.message = m.SerializeToString()
        m5 = pokemon_pb2.RequestEnvelop.Requests()
        m = pokemon_pb2.RequestEnvelop.MessageSingleString()
        m.bytes = "05daf51635c82611d1aac95c0b051d3ec088a930"
        m5.message = m.SerializeToString()

        walk = sorted(getNeighbors(float_lat,float_long))

        m1 = pokemon_pb2.RequestEnvelop.Requests()
        m1.type = 106
        m = pokemon_pb2.RequestEnvelop.MessageQuad()
        m.f1 = ''.join(map(encode, walk))
        m.f2 = "\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000"
        m.lat = f2i(float_lat) 
        m.long = f2i(float_long) 
        m1.message = m.SerializeToString()
        response = get_profile(
            access_token,
            api_endpoint,
            f2i(float_lat),
            f2i(float_long),
            response.unknown7,
            m1,
            pokemon_pb2.RequestEnvelop.Requests(),
            m4,
            pokemon_pb2.RequestEnvelop.Requests(),
            m5)
        ## Debug
        if (not response):
            print response
        payload = response.payload[0]
        heartbeat = pokemon_pb2.ResponseEnvelop.HeartbeatPayload()
        heartbeat.ParseFromString(payload)
        return heartbeat
    except Exception as e:
        print ">>>>>>>>> WARN: MAIN: Suspected login timeout - heartbeat failed."
        print e
        raise 

def session_reset():
    global SESSION 
    del SESSION
    SESSION = requests.session()
    SESSION.headers.update({'User-Agent': 'Niantic App'})
    SESSION.verify = False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", help="PTC Username", required=True)
    parser.add_argument("-p", "--password", help="PTC Password", required=True)
    parser.add_argument("-l", "--location", help="Location", required=True)
    parser.add_argument("-d", "--debug", help="Debug Mode", action='store_true')
    parser.add_argument("-s", "--search", help="Search (for): Spearow,Pidgey,Zubat,Evee (etc).", required=True)    
    parser.set_defaults(DEBUG=False)
    args = parser.parse_args()
    
    if args.debug:
        global DEBUG
        DEBUG = True
        print('[!] DEBUG mode on')

    ## Replace with better test paths later. Yes, this is hard-coded; break out the torches and pitchforks.
    stalk_core("@batman", True, args.username, args.password, args.location, args.search.split(","))
    
    
def stalk_core(slack_user, scanRepeatedly, username, password, location, searchList):

    # Geocoder flakes if called too often.   
    # BUG : Eeeeek. This is global? :/ Plz fix! (Slow refactor) - Better now.
    lat_long_alt_list = get_location(location)
    
    float_lat = lat_long_alt_list[0]
    float_long = lat_long_alt_list[1]
    orig_coords_lat = f2i(float_lat) # 0x4042bd7c00000000 # f2i(lat)
    orig_coords_long = f2i(float_long) # 0x4042bd7c00000000 # f2i(lat)
    # orig_coords_alt = f2i(lat_long_alt_list[2]) ## Ueed?
    
    starttime = time.time()
    
    while(1):
        login_time = time.time()
        
        try:
            access_token = login_ptc(username, password)
        except Exception as e:
            print ">>>>>>>>> WARN: MAIN: Login exception caught! Error follows - JSON decode issue likely...resetting Session and retrying?"
            print e
            session_reset() ## HACK BUG: Maybe best solution?
            sleep(10)
            print ">>>>>>>>> WARN: MAIN: Session reset(?) - trying login again!" 
            access_token = login_ptc(username, password)          
            pass
            
        if access_token is None:
            print('[-] Wrong username/password or refresh was not needed...')
            return
        print('[+] RPC Session Token: {} ...'.format(access_token[:25]))
        
        api_endpoint = get_api_endpoint(access_token, orig_coords_lat, orig_coords_long)
        if api_endpoint is None:
            print('[-] RPC server offline')
            return
        print('[+] Received API endpoint: {}'.format(api_endpoint))

        response = get_profile(access_token, api_endpoint, orig_coords_lat, orig_coords_long, None)
        if response is not None:
            print('[+] Login successful')
            if DEBUG:
                print(response)
            payload = response.payload[0]
            profile = pokemon_pb2.ResponseEnvelop.ProfilePayload()
            profile.ParseFromString(payload)
            print('[+] Username: {}'.format(profile.profile.username))

            creation_time = datetime.fromtimestamp(int(profile.profile.creation_time)/1000)
            print('[+] You are playing Pokemon Go since: {}'.format(
                creation_time.strftime('%Y-%m-%d %H:%M:%S'),
            ))

            for curr in profile.profile.currency:
                print('[+] {}: {}'.format(curr.type, curr.amount))
        else:
            print('[-] Ooops...')
    
        while(1):
            try:
                # Hunting four nearest cells.
                tmp_float_lat = float_lat
                tmp_float_long = float_long
                for x in range(0, int(SCAN_BLOCKS)):
                    print ">>>>>>>>> INFO: MAIN: Beginning hunt. Time elapsed is believed to be", time.time() - starttime
                    print ">>>>>>>>> INFO: MAIN: Hunting in the area around", tmp_float_lat, tmp_float_long
                    print ">>>>>>>>> INFO: MAIN: Hunting for", searchList
                    print ">>>>>>>>> INFO: MAIN: Block sweep count: ", x
                    listReturn = huntNear(api_endpoint, access_token, response, searchList, tmp_float_lat, tmp_float_long)
                    print listReturn
                    walk = getNeighbors(tmp_float_lat,tmp_float_long)
                    next = LatLng.from_point(Cell(CellId(walk[2])).get_center())     
                    tmp_float_lat =  next.lat().degrees
                    tmp_float_long = next.lng().degrees

                    if (listReturn):
                        for val in listReturn:
                            send_message(slack_user, str(val)) 
                    
                # Now need to move cells  set_location_coords(next.lat().degrees, next.lng().degrees, 0)
                if (not scanRepeatedly):
                    print ">>>>>>>>> INFO: MAIN: Breaking out - single scan only."
                    break
                print ">>>>>>>>> INFO: MAIN: Sleeping for 30 before beginning search again."
                sleep(30)
            except Exception as e:
                print ">>>>>>>>> WARN: MAIN: Exception caught! Error follows - restarting main loop/login..."
                print e
                break 
                pass
        
        if((time.time() - starttime > int(TOTAL_WORKER_LIFETIME)) or not scanRepeatedly):
            break
    
    # Hm. Ok, back up - you want each request to come in, log in once, then run a bunch of times. 
    # BUG: Eeeeek. Also refactor - NO GLOBALS! Flask: You could also use the session for simple data that is per-user.

def huntNear(api_endpoint, access_token, response, searchList, float_lat, float_long):

    origin = LatLng.from_degrees(float_lat, float_long)
    countBlocks = 0
    outputFoundList = []
    while True:
        original_lat = float_lat
        original_long = float_long
        parent = CellId.from_lat_lng(LatLng.from_degrees(float_lat, float_long)).parent(15)

        h = heartbeat(api_endpoint, access_token, response, float_lat, float_long)
        hs = [h]
        seen = set([])
        for child in parent.children():
            latlng = LatLng.from_point(Cell(child).get_center())
            # set_location_coords(latlng.lat().degrees, latlng.lng().degrees, 0)
            # latlng.lat().degrees = float lat.
            hs.append(heartbeat(api_endpoint, access_token, response, latlng.lat().degrees, latlng.lng().degrees))
        # set_location_coords(original_lat, original_long, 0)

        visible = []

        for hh in hs:
            for cell in hh.cells:
                for wild in cell.WildPokemon:
                    hash = wild.SpawnPointId + ':' + str(wild.pokemon.PokemonId)
                    if (hash not in seen):
                        visible.append(wild)
                        seen.add(hash)

        print('')
        for cell in h.cells:
            if cell.NearbyPokemon:
                other = LatLng.from_point(Cell(CellId(cell.S2CellId)).get_center())
                diff = other - origin
                # print(diff)
                difflat = diff.lat().degrees
                difflng = diff.lng().degrees
                direction = (('N' if difflat >= 0 else 'S') if abs(difflat) > 1e-4 else '')  + (('E' if difflng >= 0 else 'W') if abs(difflng) > 1e-4 else '')
                
                print("Within one step of %s (%sm %s from you):" % (other, int(origin.get_distance(other).radians * 6366468.241830914), direction))
                for poke in cell.NearbyPokemon:
                    print('    (%s) %s' % (poke.PokedexNumber, POKEMONS[poke.PokedexNumber - 1]['Name']))

        print('')
        for poke in visible:
            other = LatLng.from_degrees(poke.Latitude, poke.Longitude)
            diff = other - origin
            # print(diff)
            difflat = diff.lat().degrees
            difflng = diff.lng().degrees
            direction = (('N' if difflat >= 0 else 'S') if abs(difflat) > 1e-4 else '')  + (('E' if difflng >= 0 else 'W') if abs(difflng) > 1e-4 else '')

            pokemonFriendlyName = POKEMONS[poke.pokemon.PokemonId - 1]['Name']

            # DEBUG
            print("(%s) %s is visible at (%s, %s) for %s seconds (%sm %s from you)" % (poke.pokemon.PokemonId, pokemonFriendlyName, poke.Latitude, poke.Longitude, poke.TimeTillHiddenMs / 1000, int(origin.get_distance(other).radians * 6366468.241830914), direction))

            if pokemonFriendlyName.lower() in searchList:
                tmpStr=""
                tmpStr+=pokemonFriendlyName 
                tmpStr+=" for " 
                tmpStr+=str(int(poke.TimeTillHiddenMs / 1000)) 
                tmpStr+=" s! Distance: " 
                tmpStr+=str(int(origin.get_distance(other).radians * 6366468.241830914))
                tmpStr+="m "
                tmpStr+=direction 
                tmpStr+="! Map: "
                tmpStr+="http://maps.google.com/maps?q="
                tmpStr+=str(poke.Latitude) 
                tmpStr+="," 
                tmpStr+=str(poke.Longitude)
                outputFoundList.append(tmpStr)

#       Break loop to one-step.
#        if raw_input('The next cell is located at %s. Keep scanning? [Y/n]' % next) in {'n', 'N'}:
#            break
 
        break

    return outputFoundList

if __name__ == '__main__':
    main()

        
        
        