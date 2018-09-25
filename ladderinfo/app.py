import collections
import colorsys
import json
import random

import flask
import pyrebase
import requests
import sc2gamedata
from google.cloud import datastore


def retrieve_config_value(key: str) -> str:
    datastore_client = datastore.Client()
    return datastore_client.get(datastore_client.key("Config", key))["value"]


BLIZZARD_CLIENT_KEY = retrieve_config_value("blizzardClientKey")
BLIZZARD_CLIENT_SECRET = retrieve_config_value("blizzardClientSecret")
BOT_TOKEN = retrieve_config_value("discordBotToken")
FIREBASE_CONFIG = json.loads(retrieve_config_value("firebaseConfig"))

DISCORD_BASE_URL = 'https://discordapp.com/api/v6/'

LEAGUE_EMBLEMS = [
    "static/images/bronze.png",
    "static/images/silver.png",
    "static/images/gold.png",
    "static/images/platinum.png",
    "static/images/diamond.png",
    "static/images/master.png",
    "static/images/grandmaster.png",
]

app = flask.Flask(__name__)


@app.route("/<discord_id>")
def index(discord_id: str):
    """This is the main landing page for the app"""

    discord_user_response = requests.get(
        DISCORD_BASE_URL + "users/" + discord_id,
        headers={"Authorization": "Bot " + BOT_TOKEN},
    )

    if discord_user_response.status_code != 200:
        return "Not found", 404

    discord_data = discord_user_response.json()
    if discord_data.get("avatar", ""):
        discord_avatar = "https://cdn.discordapp.com/avatars/{}/{}".format(
            discord_id, discord_data['avatar'])
        discord_avatar_background = "white"
    else:
        discord_avatar = "static/images/discord-face.png"
        rand = random.Random()
        rand.seed(discord_id)
        r, g, b = colorsys.hsv_to_rgb(rand.uniform(0, 1), 0.5, 0.8)
        discord_avatar_background = "rgba({}, {}, {}, 255)".format(255 * r, 255 * g, 255 * b)
    discord_username = discord_data.get("username", "")

    db = pyrebase.initialize_app(FIREBASE_CONFIG).database()
    user_data = db.child("members").child(discord_id).get().val()
    if not user_data:
        user_data = {}

    discord_guild_member_response = requests.get(
        DISCORD_BASE_URL + "guilds/154861527906779136/members/" + discord_id,
        headers={
            "Authorization": "Bot " + BOT_TOKEN
        })

    if discord_guild_member_response.status_code == 200:
        discord_guild_member_data = discord_guild_member_response.json()
        name = discord_guild_member_data.get("nick", "")
    else:
        name = ""
    if not name:
        name = user_data.get("discord_display_name",
                             user_data.get("discord_server_nick", discord_username))

    access_token_response = sc2gamedata.get_access_token(BLIZZARD_CLIENT_KEY,
                                                         BLIZZARD_CLIENT_SECRET, "us")

    eu_current_season_response = sc2gamedata.get_current_season_data(access_token_response[0], "eu")
    eu_current_season = str(eu_current_season_response.get("id", ""))

    us_current_season_response = sc2gamedata.get_current_season_data(access_token_response[0], "us")
    us_current_season = str(us_current_season_response.get("id", ""))

    kr_current_season_response = sc2gamedata.get_current_season_data(access_token_response[0], "kr")
    kr_current_season = str(kr_current_season_response.get("id", ""))

    eu_characters = list(user_data.get("characters", {}).get("eu", {}).values())
    us_characters = list(user_data.get("characters", {}).get("us", {}).values())
    kr_characters = list(user_data.get("characters", {}).get("kr", {}).values())

    def sorted_ladder_info(unsorted_ladder_info: dict) -> collections.OrderedDict:
        return collections.OrderedDict(
            sorted(unsorted_ladder_info.items(), key=lambda x: x[1]["mmr"], reverse=True))

    for character in eu_characters + us_characters + kr_characters:
        if not character.get("avatar", ""):
            character["avatar"] = "http://media.blizzard.com/sc2/portraits/0-0.jpg"

        for races in character.get("ladder_info", {}).values():
            for race_ladder_info in races.values():
                race_ladder_info["league_emblem"] = LEAGUE_EMBLEMS[race_ladder_info.get(
                    "league_id", 0)]

    for character in eu_characters:
        if "ladder_info" in character:
            ladder_info = character.get("ladder_info", {}).get(eu_current_season, {})
            if ladder_info:
                character["ladder_info"] = sorted_ladder_info(ladder_info)
            else:
                character.pop("ladder_info")

    for character in us_characters:
        if "ladder_info" in character:
            ladder_info = character["ladder_info"].get(us_current_season, {})
            if ladder_info:
                character["ladder_info"] = sorted_ladder_info(ladder_info)
            else:
                character.pop("ladder_info")

    for character in kr_characters:
        if "ladder_info" in character:
            ladder_info = character["ladder_info"].get(kr_current_season, {})
            if ladder_info:
                character["ladder_info"] = sorted_ladder_info(ladder_info)
            else:
                character.pop("ladder_info")

    def sort_characters_key(character_data: dict):
        return max(
            (race['mmr'] for race in character_data.get("ladder_info", {}).values()), default=0)

    eu_characters.sort(key=sort_characters_key, reverse=True)
    us_characters.sort(key=sort_characters_key, reverse=True)
    kr_characters.sort(key=sort_characters_key, reverse=True)

    return flask.render_template(
        "root.html.j2", **{
            "name": name,
            "battle_tag": user_data.get("battle_tag", ""),
            "discord_avatar": discord_avatar,
            "discord_avatar_background": discord_avatar_background,
            "eu_characters": eu_characters,
            "us_characters": us_characters,
            "kr_characters": kr_characters,
        })
