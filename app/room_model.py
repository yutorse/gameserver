import json
import uuid
from enum import Enum, IntEnum
from typing import Optional

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound

from .db import engine


class LiveDifficulty(IntEnum):
    normal = 1
    hard = 2


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
