import urllib.parse
from typing import Type, Dict

from aiohttp.web import Request, Response, json_response
from mautrix.types import RoomID
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from maubot import Plugin, MessageEvent
from maubot.handlers import command, web


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("api_key")


class PocketPlugin(Plugin):
    @web.get("/authorize")
    async def authorize(self, request: Request) -> Response:
        # TODO get code and room from database
        token = "foobar"
        room_id = RoomID("!foobar:foo.bar")
        user = await self.pocket_authorize(token)
        if user.get("error_code"):
            await self.client.send_text(
                room_id,
                f"Failed to fetch user details, response code: {user.get('error_code')}",
            )
        # TODO store access token in db
        return json_response({})

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    @command.new("pocket")
    async def handler(self, event: MessageEvent) -> None:
        await event.mark_read()
        # TODO raise if not authed, otherwise fetch random article
        await event.respond("Woop woop")

    @handler.subcommand(help="Authenticate with pocket")
    async def login(self, event: MessageEvent):
        # TODO raise if logged in
        token = await self.pocket_obtain_request_token()
        if token.get("error_code"):
            return await event.respond(
                f"Failed to initialize authentication flow, response code: {token.get('error_code')}",
            )
        redirect_url = urllib.parse.quote(f"{self.webapp_url}/authorize")
        await event.respond(
            f"Please continue by going to the following url and allowing access to your Pocket account: "
            f"https://getpocket.com/auth/authorize?request_token={token.get('request_token')}"
            f"&redirect_uri={redirect_url}"
        )

    @handler.subcommand(help="Disconnect from Pocket")
    async def logout(self, event: MessageEvent) -> None:
        # TODO implement
        pass

    async def pocket_authorize(self, token: str) -> Dict:
        response = await self.http.post(
            "https://getpocket.com/v3/oauth/authorize",
            headers={
                "X-Accept": "application/json",
            },
            json={
                "consumer_key": self.config["api_key"],
                "code": token,
            },
        )
        if response.status != 200:
            self.log.warning(f"Unexpected status obtaining access token: {response.status}")
            return {
                "access_token": None,
                "error_code": response.status,
                "username": None,
            }
        data = await response.json()
        if not data.get("access_token"):
            self.log.warning(f"No access token found when obtaining request token")
            return {
                "access_token": None,
                "error_code": 500,
                "username": None,
            }
        return {
            "access_token": data.get("access_token"),
            "error_code": None,
            "username": data.get("username"),
        }

    async def pocket_obtain_request_token(self) -> Dict:
        response = await self.http.post(
            "https://getpocket.com/v3/oauth/request",
            headers={
                "X-Accept": "application/json",
            },
            json={
                "consumer_key": self.config["api_key"],
                "redirect_uri": f"{self.webapp_url}/authorize",
            },
        )
        if response.status != 200:
            self.log.warning(f"Unexpected status obtaining request token: {response.status}")
            return {
                "error_code": response.status,
                "request_token": None,
            }
        data = await response.json()
        if not data.get("code"):
            self.log.warning(f"No request token found when obtaining request token")
            return {
                "error_code": 500,
                "request_token": None,
            }
        return {
            "error_code": None,
            "request_token": data.get("code"),
        }

    async def start(self) -> None:
        await super().start()
        self.config.load_and_update()
