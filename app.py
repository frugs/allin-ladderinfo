import asyncio
import os
import pickle

import aiohttp
import aiohttp.web
import aiohttp_jinja2
import jinja2
import pyrebase
import sc2gamedata

from typing import Union

BLIZZARD_CLIENT_KEY = os.getenv("BLIZZARD_CLIENT_KEY")
BLIZZARD_CLIENT_SECRET = os.getenv("BLIZZARD_CLIENT_SECRET")
DISCORD_BASE_URL = 'https://discordapp.com/api/v6/'


@aiohttp_jinja2.template('root.html.j2')
async def root(request: aiohttp.web.Request) -> Union[dict, aiohttp.web.Response]:
    """This is the main landing page for the app"""
    discord_id = request.match_info['discord_id']

    discord_user_response = await aiohttp.request(
        "GET",
        DISCORD_BASE_URL + "users/" + discord_id,
        headers={"Authorization": "Bot " + "MjIwNjMyODc5NjE1NDQyOTQ0.DS2nQg.0aurWqsie2PgdqLq-7g0vIdBWjE"})

    if discord_user_response.status == 200:
        discord_data = await discord_user_response.json()
        discord_avatar = "https://cdn.discordapp.com/avatars/{}/{}".format(discord_id, discord_data['avatar'])

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
        for character in eu_characters:
            ladder_info = character.get("ladder_info", {}).get(eu_current_season, {})
            if ladder_info:
                character["ladder_info"] = ladder_info
            else:
                character.pop("ladder_info")

        us_characters = list(user_data.get("characters", {}).get("us", {}).values())
        for character in us_characters:
            ladder_info = character.get("ladder_info", {}).get(us_current_season, {})
            if ladder_info:
                character["ladder_info"] = ladder_info
            else:
                character.pop("ladder_info")

        return {
            "name": user_data.get("discord_display_name", user_data.get("discord_server_nick", "")),
            "battle_tag": user_data.get("battle_tag", ""),
            "discord_avatar": discord_avatar,
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
