import urllib.parse
from typing import Type, Dict
from uuid import uuid4

from aiohttp.web import Request, Response, json_response
from mautrix.types import UserID
from mautrix.util.config import BaseProxyConfig, ConfigUpdateHelper
from maubot import Plugin, MessageEvent
from maubot.handlers import command, web
from sqlalchemy.exc import DBAPIError

from pocket.db import Database


class Config(BaseProxyConfig):
    def do_update(self, helper: ConfigUpdateHelper) -> None:
        helper.copy("api_key")


class PocketPlugin(Plugin):
    db: Database

    @web.get("/authorize/{request_state}")
    async def authorize(self, request: Request) -> Response:
        request_state = request.match_info.get("request_state")
        if not request_state:
            return json_response({}, status=400)

        user = self.db.get_user_by_request_state(request_state)
        if not user:
            return json_response({}, status=400)

        data = await self.pocket_authorize(user.request_token)
        if data.get("error_code"):
            self.log.warning(f"Got error code from pocket authorization: {data.get('error_code')}")
            await self.client.send_notice(
                user.request_room,
                f"Failed to connect to Pocket, response code: {data.get('error_code')}",
            )
            return json_response({}, status=400)
        try:
            self.db.set_user_access_token(UserID(user.user_id), data.get("access_token"))
        except DBAPIError as ex:
            self.log.exception(f"Failed to set access token to database: {ex}")
            await self.client.send_notice(
                user.request_room,
                f"Failed to connect to Pocket due to database error. Please try again.",
            )
            return json_response({}, status=400)
        self.log.info(f"User {user.user_id} successfully connected to Pocket")
        await self.client.send_notice(
            user.request_room,
            f"Successfully connected to Pocket! Use `!pocket` to get a random article.",
        )
        # TODO make all responses render a web page, not JSON
        return json_response({})

    @classmethod
    def get_config_class(cls) -> Type[BaseProxyConfig]:
        return Config

    @command.new("pocket")
    async def handler(self, event: MessageEvent) -> None:
        await event.mark_read()
        # TODO raise if not authed, otherwise fetch random article
        await event.respond("Woop woop")

    @handler.subcommand(help="Authenticate with Pocket")
    async def login(self, event: MessageEvent) -> None:
        user = self.db.get_user_by_id(event.sender)
        if user and user.access_token:
            await event.respond(
                "You're already logged into Pocket. Use `logout` to clear the current access token."
            )
            return
        request_state = str(uuid4())
        token = await self.pocket_obtain_request_token(request_state)
        if token.get("error_code"):
            self.log.warning(f"Failed to obtain request token, error from Pocket: {token.get('error_code')}")
            await event.respond(
                f"Failed to initialize authentication flow, response code: {token.get('error_code')}",
            )
            return
        redirect_url = urllib.parse.quote(f"{self.webapp_url}/authorize/{request_state}")
        try:
            self.db.set_user_request_token(event.sender, event.room_id, token.get("request_token"), request_state)
        except DBAPIError as ex:
            self.log.exception(f"Failed to store request token to database: {ex}")
            await event.respond("Failed to store request token, please try `login` again.")
            return
        await event.respond(
            f"Please continue by going to the following url and allowing access to your Pocket account: "
            f"https://getpocket.com/auth/authorize?request_token={token.get('request_token')}"
            f"&redirect_uri={redirect_url}"
        )

    @handler.subcommand(help="Disconnect from Pocket")
    async def logout(self, event: MessageEvent) -> None:
        user = self.db.get_user_by_id(event.sender)
        if not user or not user.access_token:
            await event.respond("You're not logged into Pocket.")
            return
        # TODO also nuke token on Pocket side
        try:
            self.db.set_user_access_token(event.sender, "")
        except DBAPIError as ex:
            self.log.exception(f"Failed to clear user access token: {ex}")
            await event.respond("Failed to clear access token, please contact bot admin.")
            return
        await event.respond("Successfully disconnected from Pocket.")

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
            }
        data = await response.json()
        if not data.get("access_token"):
            self.log.warning(f"No access token found when obtaining request token")
            return {
                "access_token": None,
                "error_code": 500,
            }
        return {
            "access_token": data.get("access_token"),
            "error_code": None,
        }

    async def pocket_obtain_request_token(self, request_state: str) -> Dict:
        response = await self.http.post(
            "https://getpocket.com/v3/oauth/request",
            headers={
                "X-Accept": "application/json",
            },
            json={
                "consumer_key": self.config["api_key"],
                "redirect_uri": f"{self.webapp_url}/authorize/{request_state}",
                "state": request_state,
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
        self.db = Database(self.database)
