import json
import uuid
from enum import Enum, IntEnum
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound

from .db import engine

MAX_USER_COUNT = 4 # 部屋に入れる最大人数

class LiveDifficulty(IntEnum):
    normal = 1
    hard = 2


class RoomInfo(BaseModel):
    room_id: int
    live_id: int
    joined_user_count: int
    max_user_count: int = MAX_USER_COUNT


def create_room(live_id: int) -> int:
    """Create new room and returns room_id"""
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO `room` (live_id, joined_user_count) VALUES (:live_id, 1)"
            ),
            dict(live_id=live_id),
        )
        room_id = result.lastrowid  # 最後の行を参照することで room_id を取得
    return room_id


def get_room_list(live_id: int) -> Optional[RoomInfo]: # roomが存在しないときは空リストを返す。
    """Search available rooms"""
    available_rooms = []
    with engine.begin() as conn:
        if live_id == 0:
            result = conn.execute(
                text(
                    "SELECT `room_id`, `live_id`, `joined_user_count` FROM `room`"
                ),
            )
        else:
            result = conn.execute(
                text(
                    "SELECT `room_id`, `live_id`, `joined_user_count` FROM `room` WHERE `live_id`=:live_id"
                ),
                dict(live_id=live_id),
            )
        result = result.all()
        for row in result:
            available_rooms.append(RoomInfo(room_id=row.room_id, live_id=row.live_id, joined_user_count=row.joined_user_count))
        return available_rooms
