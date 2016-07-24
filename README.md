# Pokemon Go API Poller, with slack integration.

* Many thanks to https://github.com/AHAAAAAAA/PokemonGo-Map and all it's contributors!
* WARNING: Definitely violates the TOS. Don't run this with your own account!
* includes protobuf file
* maybe you should change some of the proto values like gps cords...
* ugly code


Usage (Prep):

 * Go to slack and configure two slash commands to route to https://(server)/poke-ping and /poke-scan and token secret.
 * Get ngrok or other flask hosting.

Usage (Running): 
 * source venv/bin/activate + ngrok as needed.
 * Set env vars (and slack integrations!):
 * SLACK_SLASH_SECRET_PULSE = os.environ.get('SLACK_SLASH_SECRET_PULSE') (same as 'ping')
 * SLACK_SLASH_SECRET_SCAN = os.environ.get('SLACK_SLASH_SECRET_SCAN')
 * POKEMON_TEST_USER = os.environ.get('POKEMON_TEST_USER')  
 * POKEMON_TEST_PASSWORD = os.environ.get('POKEMON_TEST_PASSWORD')
 * SLACK_TOKEN = os.environ.get('SLACK_TOKEN', None)
 * python recieve.py 
