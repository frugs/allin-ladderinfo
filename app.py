import asyncio
import colorsys
import os
import random
import pickle

import aiohttp
import aiohttp.web
import aiohttp_jinja2
import jinja2
import pyrebase
import sc2gamedata

from typing import Union

BLIZZARD_CLIENT_KEY = os.getenv("BLIZZARD_CLIENT_KEY", "")
BLIZZARD_CLIENT_SECRET = os.getenv("BLIZZARD_CLIENT_SECRET", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

DISCORD_BASE_URL = 'https://discordapp.com/api/v6/'

LEAGUE_EMBLEMS = [
    "static/images/bronze.png",
    "static/images/silver.png",
    "static/images/gold.png",
    "static/images/platinum.png",
    "static/images/diamond.png",
    "static/images/master.png",
    "static/images/grandmaster.png"
]


@aiohttp_jinja2.template('root.html.j2')
async def root(request: aiohttp.web.Request) -> Union[dict, aiohttp.web.Response]:
    """This is the main landing page for the app"""
    discord_id = request.match_info['discord_id']

    discord_user_response = await aiohttp.request(
        "GET",
        DISCORD_BASE_URL + "users/" + discord_id,
        headers={"Authorization": "Bot " + BOT_TOKEN})

    if discord_user_response.status == 200:
        discord_data = await discord_user_response.json()
        if discord_data.get("avatar", ""):
            discord_avatar = "https://cdn.discordapp.com/avatars/{}/{}".format(discord_id, discord_data['avatar'])
            discord_avatar_background = "white"
        else:
            discord_avatar = "static/images/discord-face.png"
            rand = random.Random()
            rand.seed(discord_id)
            r, g, b = colorsys.hsv_to_rgb(rand.uniform(0, 1), 0.5, 0.8)
            discord_avatar_background = "rgba({}, {}, {}, 255)".format(255 * r, 255 * g, 255 * b)

        with open("firebase.cfg", "rb") as file:
            db_config = pickle.load(file)

        db = pyrebase.initialize_app(db_config).database()
        user_data = db.child("members").child(discord_id).get().val()
        if not user_data:
            user_data = {}

        access_token_response = await asyncio.get_event_loop().run_in_executor(
            None, sc2gamedata.get_access_token, BLIZZARD_CLIENT_KEY, BLIZZARD_CLIENT_SECRET, "us")

        eu_current_season_response = await asyncio.get_event_loop().run_in_executor(
            None, sc2gamedata.get_current_season_data, access_token_response[0], "eu")
        eu_current_season = str(eu_current_season_response.get("id", ""))

        us_current_season_response = await asyncio.get_event_loop().run_in_executor(
            None, sc2gamedata.get_current_season_data, access_token_response[0], "us")
        us_current_season = str(us_current_season_response.get("id", ""))

        eu_characters = list(user_data.get("characters", {}).get("eu", {}).values())
        us_characters = list(user_data.get("characters", {}).get("us", {}).values())

        for character in eu_characters + us_characters:
            if not character.get("avatar", ""):
                character["avatar"] = "http://media.blizzard.com/sc2/portraits/0-0.jpg"

            for races in character.get("ladder_info", {}).values():
                for race_ladder_info in races.values():
                    race_ladder_info["league_emblem"] = LEAGUE_EMBLEMS[race_ladder_info.get("league_id", 0)]

        for character in eu_characters:
            if "ladder_info" in character:
                ladder_info = character.get("ladder_info", {}).get(eu_current_season, {})
                if ladder_info:
                    character["ladder_info"] = ladder_info
                else:
                    character.pop("ladder_info")

        for character in us_characters:
            if "ladder_info" in character:
                ladder_info = character["ladder_info"].get(us_current_season, {})
                if ladder_info:
                    character["ladder_info"] = ladder_info
                else:
                    character.pop("ladder_info")

        return {
            "name": user_data.get("discord_display_name", user_data.get("discord_server_nick", "")),
            "battle_tag": user_data.get("battle_tag", ""),
            "discord_avatar": discord_avatar,
            "discord_avatar_background": discord_avatar_background,
            "eu_characters": eu_characters,
            "us_characters": us_characters,
        }
    else:
        return aiohttp.web.HTTPNotFound()


def main():
    app = aiohttp.web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('templates/'))

    app.router.add_static('/static/', 'static/')

    resource = app.router.add_resource('/{discord_id}')
    resource.add_route('GET', root)

    aiohttp.web.run_app(app, port=5002)


if __name__ == "__main__":
    main()
