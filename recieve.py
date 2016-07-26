import os
from flask import Flask, request, Response
import core
from time import sleep
import multiprocessing as mp
from multiprocessing import Process
import shlex
from unidecode import unidecode

app = Flask(__name__)

SLACK_SLASH_SECRET_PULSE = os.environ.get('SLACK_SLASH_SECRET_PULSE')
SLACK_SLASH_SECRET_SCAN = os.environ.get('SLACK_SLASH_SECRET_SCAN')
POKEMON_TEST_USER = os.environ.get('POKEMON_TEST_USER')
POKEMON_TEST_PASSWORD = os.environ.get('POKEMON_TEST_PASSWORD')

@app.route('/poke-ping', methods=['POST'])
def pollOnce():
    if request.form.get('token') == SLACK_SLASH_SECRET_PULSE:
        # channel = request.form.get('channel_name')
        username = request.form.get('user_name')
        text = request.form.get('text')
        # inbound_message = username + " in " + channel + " says: " + text
        # print(inbound_message)
        print("Invoking scan once...")
        # Response(), 200      
        if(not try_parse_message_pulse(text)):
            core.send_message( "@" + username, "Bad request! Syntax is: " + request.form.get('command') + " \"Address\" -- including quotes!") 
        else:
            core.send_message( "@" + username, "Kicking off a single-sweep for all pokemon near: "+ text) 
            q = mp.Queue()
            list_all_poke = "Bulbasaur,Ivysaur,Venusaur,Charmander,Charmeleon,Charizard,Squirtle,Wartortle,Blastoise,Caterpie,Metapod,Butterfree,Weedle,Kakuna,Beedrill,Pidgey,Pidgeotto,Pidgeot,Rattata,Raticate,Spearow,Fearow,Ekans,Arbok,Pikachu,Raichu,Sandshrew,Sandslash,NidoranF,Nidorina,Nidoqueen,NidoranM,Nidorino,Nidoking,Clefairy,Clefable,Vulpix,Ninetales,Jigglypuff,Wigglytuff,Zubat,Golbat,Oddish,Gloom,Vileplume,Paras,Parasect,Venonat,Venomoth,Diglett,Dugtrio,Meowth,Persian,Psyduck,Golduck,Mankey,Primeape,Growlithe,Arcanine,Poliwag,Poliwhirl,Poliwrath,Abra,Kadabra,Alakazam,Machop,Machoke,Machamp,Bellsprout,Weepinbell,Victreebell,Tentacool,Tentacruel,Geodude,Graveler,Golum,Ponyta,Rapidash,Slowpoke,Slowbro,Magnemite,Magneton,Farfetch'd,Doduo,Dodrio,Seel,Dewgong,Grimer,Muk,Shellder,Cloyster,Gastly,Haunter,Gengar,Onix,Drowzee,Hypno,Krabby,Kingler,Voltorb,Electrode,Exeggcute,Exeggutor,Cubone,Marowak,Hitmonlee,Hitmonchan,Lickitung,Koffing,Weezing,Rhyhorn,Rhydon,Chansey,Tangela,Kangaskhan,Horsea,Seadra,Goldeen,Seaking,Staryu,Starmie,MrMime,Scyther,Jynx,Electabuzz,Magmar,Pinsir,Tauros,Magikarp,Gyarados,Lapras,Ditto,Eevee,Vaporeon,Jolteon,Flareon,Porygon,Omanyte,Omastar,Kabuto,Kabutops,Aerodactyl,Snorlax,Articuno,Zapdos,Moltres,Dratini,Dragonair,Dragonite,Mewtwo,Mew"
            p = mp.Process(target=longtask, args=(username, False, text, list_all_poke.lower().split(","),))
            p.start()
            print("Kicked background action to poke-poll!")
        # core.stalk_core(text) 
        # Make this do poke-poll for an hour, responding to me.  
    return Response(), 200
    
    
@app.route('/poke-scan', methods=['POST'])
def stalker():
    if request.form.get('token') == SLACK_SLASH_SECRET_SCAN:
        # channel = request.form.get('channel_name')
        username = request.form.get('user_name')
        text = request.form.get('text')
        # inbound_message = username + " in " + channel + " says: " + text
        # print(inbound_message)
        print("Invoking Stalker...")
        # Response(), 200      
        if(not try_parse_message_poll(text)):
            core.send_message( "@" + username, "Bad request! Syntax is: " + request.form.get('command') + " \"Address\" \"Comma,separated,list,of,pokemon\" -- including quotes!") 
        else:
            core.send_message( "@" + username, "Kicking off a pokemon poll for one hour for: "+ text) 
            q = mp.Queue()
            p = mp.Process(target=longtask, args=(username, True, shlex.split(unidecode(text))[0],shlex.split(unidecode(text))[1].lower().split(","),))
            p.start()
            print("Kicked background action to poke-poll!")
        # core.stalk_core(text) 
        # Make this do poke-poll for an hour, responding to me.  
    return Response(), 200
 
@app.route('/', methods=['GET'])
def test():
    return Response('It works!')

def try_parse_message_pulse(text):
    try:
        arg_try = shlex.split(unidecode(text))
        print(arg_try)
        print(len(arg_try))
    
        if len(arg_try) != 1:
            return False
        if len(arg_try[0]) == 0:
            return False
        return True
    except:
        print("Oops...")
        return False
        
def try_parse_message_poll(text):
    try:
        arg_try = shlex.split(unidecode(text))
        print(arg_try)
        print(len(arg_try))
    
        if len(arg_try) != 2:
            return False
        if len(arg_try[1]) == 0:
            return False
        return True
    except:
        print("Oops...")
        return False



def longtask(username, repeatScan, location, pokeList):
    print("Starting....")
    # core.stalk_core(text) 
    core.stalk_core("@" + username, repeatScan, POKEMON_TEST_USER, POKEMON_TEST_PASSWORD, location, pokeList)
    print("...Finishing!")
     
if __name__ == "__main__":
    app.run(threaded=True,debug=True)
