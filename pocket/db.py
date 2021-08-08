from datetime import datetime
from typing import NamedTuple, Optional

from mautrix.types import UserID, RoomID, EventID
from sqlalchemy import (
    Column, String, Integer, DateTime, Table, MetaData, select, and_,
)
from sqlalchemy.engine.base import Engine
from sqlalchemy.exc import IntegrityError

Event = NamedTuple(
    "Event",
    id=int,
    event_id=EventID,
    item_id=str,
    user_id=UserID,
)

User = NamedTuple(
    "User",
    id=int,
    user_id=UserID,
    access_token=str,
    request_room=RoomID,
    request_token=str,
    request_token_date=datetime,
    request_state=str,
)


class Database:
    db: Engine
    user: Table
    version: Table

    def __init__(self, db: Engine) -> None:
        self.db = db
        metadata = MetaData()
        self.user = Table(
            "users",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("user_id", String(255), nullable=False, unique=True),
            Column("access_token", String(255), nullable=False, default=""),
            Column("request_room", String(255), nullable=False, default=""),
            Column("request_token", String(255), nullable=False, default=""),
            Column("request_token_date", DateTime, nullable=True),
            Column("request_state", String(255), nullable=False, default=""),
        )
        self.event = Table(
            "events",
            metadata,
            Column("id", Integer, primary_key=True, autoincrement=True),
            Column("event_id", String(255), nullable=False, unique=True),
            Column("item_id", String(255), nullable=False),
            Column("user_id", String(255), nullable=False),
        )
        self.version = Table(
            "version",
            metadata,
            Column("version", Integer, primary_key=True),
        )
        self.upgrade()

    def get_user_by_id(self, user_id: str) -> Optional[User]:
        rows = self.db.execute(
            select([self.user]).where(self.user.c.user_id == user_id)
        )
        try:
            row = next(rows)
            return User(*row)
        except (ValueError, StopIteration):
            return None

    def get_user_by_request_state(self, request_state: str) -> Optional[User]:
        rows = self.db.execute(
            select([self.user]).where(self.user.c.request_state == request_state)
        )
        try:
            row = next(rows)
            return User(*row)
        except (ValueError, StopIteration):
            return None

    def get_user_event(self, user_id: UserID, event_id: EventID):
        rows = self.db.execute(
            select([self.event]).where(and_(self.event.c.user_id == user_id, self.event.c.event_id == event_id))
        )
        try:
            row = next(rows)
            return Event(*row)
        except (ValueError, StopIteration):
            return None

    def set_user_access_token(self, user_id: UserID, access_token: str) -> None:
        self.db.execute(
            self.user.update()
                .where(self.user.c.user_id == user_id)
                .values(
                    access_token=access_token,
                    request_room="",
                    request_token="",
                    request_token_date=None,
                    request_state="",
                ),
        )

    def set_user_request_token(self, user_id: UserID, room_id: RoomID, request_token: str, request_state: str) -> None:
        try:
            self.db.execute(
                self.user.insert()
                    .values(
                        user_id=user_id,
                        request_room=room_id,
                        request_token=request_token,
                        request_token_date=datetime.utcnow(),
                        request_state=request_state,
                    ),
            )
        except IntegrityError:
            self.db.execute(
                self.user.update()
                    .where(self.user.c.user_id == user_id)
                    .values(
                        request_room=room_id,
                        request_token=request_token,
                        request_token_date=datetime.utcnow(),
                        request_state=request_state,
                    ),
            )

    def store_user_event(self, user_id: UserID, event_id: EventID, item_id: str) -> None:
        self.db.execute(
            self.event.insert()
                .values(
                    event_id=event_id,
                    item_id=item_id,
                    user_id=user_id,
                ),
        )

    def upgrade(self) -> None:
        self.db.execute("CREATE TABLE IF NOT EXISTS version (version INTEGER PRIMARY KEY)")
        try:
            version, = next(self.db.execute(select([self.version.c.version])))
        except (StopIteration, IndexError):
            version = 0
        if version == 0:
            self.db.execute("""CREATE TABLE IF NOT EXISTS users (
                id INTEGER NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                access_token VARCHAR(255) NOT NULL DEFAULT '',
                request_room VARCHAR(255) NOT NULL DEFAULT '',
                request_token VARCHAR(255) NOT NULL DEFAULT '',
                request_token_date DATETIME NULL,
                request_state VARCHAR(255) NOT NULL DEFAULT '',
                PRIMARY KEY (id),
                UNIQUE (user_id)
            )""")
            version = 1
        if version == 1:
            self.db.execute("""CREATE TABLE IF NOT EXISTS events (
                id INTEGER NOT NULL,
                event_id VARCHAR(255) NOT NULL,
                item_id VARCHAR(255) NOT NULL,
                user_id VARCHAR(255) NOT NULL,
                PRIMARY KEY (id),
                UNIQUE (event_id)
            )""")
            version = 2
        self.db.execute(self.version.delete())
        self.db.execute(self.version.insert().values(version=version))
