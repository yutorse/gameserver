import json
import uuid
from curses import REPORT_MOUSE_POSITION
from enum import Enum, IntEnum
from typing import List, Optional, Tuple

from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import NoResultFound

from . import model
from .db import engine
from .model import SafeUser

MAX_USER_COUNT = 4  # 部屋に入れる最大人数


class LiveDifficulty(IntEnum):
    normal = 1
    hard = 2


class JoinRoomResult(IntEnum):
    Ok = 1
    RoomFull = 2
    Disbanded = 3
    OtherError = 4


class WaitRoomStatus(IntEnum):
    Waiting = 1
    LiveStart = 2
    Dissolution = 3


class RoomInfo(BaseModel):
    room_id: int
    live_id: int
    joined_user_count: int
    max_user_count: int = MAX_USER_COUNT


class RoomUser(BaseModel):
    user_id: int
    name: str
    leader_card_id: int
    select_difficulty: LiveDifficulty
    is_me: bool
    is_host: bool


class ResultUser(BaseModel):
    user_id: int
    judge_count_list: List[int]
    score: int


def create_room(live_id: int, select_difficulty: LiveDifficulty, token: str) -> int:
    """Create new room and returns room_id"""
    user_id = model.get_user_by_token(token).id
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "INSERT INTO `room` (live_id, joined_user_count, status, host) VALUES (:live_id, 1, 1, :user_id)"
            ),
            dict(live_id=live_id, user_id=user_id),
        )
        room_id = result.lastrowid  # 最後の行を参照することで room_id を取得
        conn.execute(
            text(
                "INSERT INTO `room_members` (room_id, user_id, select_difficulty, token) VALUES (:room_id, :user_id, :select_difficulty, :token)"
            ),
            dict(
                room_id=room_id,
                user_id=user_id,
                select_difficulty=select_difficulty.value,
                token=token,
            ),
        )
    return room_id


def get_room_list(live_id: int) -> List[RoomInfo]:  # roomが存在しないときは空リストを返す。
    """Search available rooms"""
    available_rooms = []
    with engine.begin() as conn:
        if live_id == 0:
            result = conn.execute(
                text("SELECT `room_id`, `live_id`, `joined_user_count` FROM `room`"),
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
            available_rooms.append(
                RoomInfo(
                    room_id=row.room_id,
                    live_id=row.live_id,
                    joined_user_count=row.joined_user_count,
                )
            )
        return available_rooms


def join_room(room_id: int, select_difficulty: int, token: str) -> JoinRoomResult:
    """join the room specified by room_id"""
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "SELECT `room_id`, `live_id`, `joined_user_count` FROM `room` WHERE `room_id`=:room_id"
            ),
            dict(room_id=room_id),
        )
        try:
            row = result.one()
            if row.joined_user_count < MAX_USER_COUNT:
                query = (
                    "UPDATE `room` SET `joined_user_count`=:increment_user_count WHERE `room_id`=:room_id;"
                    "INSERT INTO `room_members` (room_id, user_id, select_difficulty, token) VALUES (:room_id, :user_id, :select_difficulty, :token)"
                )
                conn.execute(
                    text(query),
                    dict(
                        increment_user_count=(row.joined_user_count + 1),
                        room_id=room_id,
                        user_id=model.get_user_by_token(token).id,
                        select_difficulty=select_difficulty,
                        token=token,
                    ),
                )
                return JoinRoomResult.Ok
            else:
                return JoinRoomResult.RoomFull
        except NoResultFound:
            return JoinRoomResult.Disbanded
        # except:
        # return JoinRoomResult.OtherError


def get_room_status(conn, room_id: int) -> WaitRoomStatus:
    result = conn.execute(
        text("SELECT `status` FROM `room` WHERE `room_id`=:room_id"),
        dict(room_id=room_id),
    )
    try:
        row = result.one()
        if row.status == 1:
            return WaitRoomStatus.Waiting
        elif row.status == 2:
            return WaitRoomStatus.LiveStart
        else:
            return WaitRoomStatus.Dissolution
    except NoResultFound:
        return WaitRoomStatus.Dissolution


def get_room_host(conn, room_id: int) -> Optional[str]:
    result = conn.execute(
        text("SELECT `host` FROM `room` WHERE `room_id`=:room_id"),
        dict(room_id=room_id),
    )
    try:
        row = result.one()
        return row.host
    except NoResultFound:
        return None


def get_room_users(conn, room_id: int, token: str) -> List[RoomUser]:
    room_users = []
    host: str = get_room_host(conn, room_id)
    result = conn.execute(
        text(
            "SELECT `user_id`, `select_difficulty`, `token` FROM `room_members` WHERE `room_id`=:room_id"
        ),
        dict(room_id=room_id),
    )
    result = result.all()
    for row in result:
        user_info: SafeUser = model.get_user_by_token(row.token)
        room_users.append(
            RoomUser(
                user_id=row.user_id,
                name=user_info.name,
                leader_card_id=user_info.leader_card_id,
                select_difficulty=row.select_difficulty,
                is_me=(token == row.token),
                is_host=(host == row.user_id),
            )
        )
    return room_users


def wait_room(room_id: int, token: str) -> Tuple[WaitRoomStatus, List[RoomUser]]:
    with engine.begin() as conn:
        room_status = get_room_status(conn, room_id)
        room_users = get_room_users(conn, room_id, token)
    return (room_status, room_users)


def start_room(room_id: int, token: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE `room` SET `status`=2 WHERE `room_id`=:room_id"),
            dict(room_id=room_id),
        )
    return None


def finish_room(
    room_id: int, score: int, judge_count_list: List[int], token: str
) -> None:
    perfect_count = judge_count_list[0]
    great_count = judge_count_list[1]
    good_count = judge_count_list[2]
    bad_count = judge_count_list[3]
    miss_count = judge_count_list[4]
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE `room_members` SET `status`=2, `score`=:score, `perfect`=:perfect, `great`=:great, `good`=:good, `bad`=:bad, `miss`=:miss WHERE `room_id`=:room_id AND`token`=:token"
            ),
            dict(
                score=score,
                perfect=perfect_count,
                great=great_count,
                good=good_count,
                bad=bad_count,
                miss=miss_count,
                room_id=room_id,
                token=token,
            ),
        )
    return None


def show_result(room_id: int) -> List[ResultUser]:
    user_result_list = []
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "SELECT `user_id`, `status`, `score`, `perfect`, `great`, `good`, `bad`, `miss` FROM `room_members` WHERE `room_id`=:room_id"
            ),
            dict(
                room_id=room_id,
            ),
        )
        result = result.all()
        for row in result:
            if row.status == 1:
                return []  # まだ全員がリザルト画面に遷移していない場合
            user_result_list.append(
                ResultUser(
                    user_id=row.user_id,
                    judge_count_list=[
                        row.perfect,
                        row.great,
                        row.good,
                        row.bad,
                        row.miss,
                    ],
                    score=row.score,
                )
            )
        conn.execute(
            text("UPDATE `room` SET `status`=3 WHERE `room_id`=:room_id"),
            dict(room_id=room_id),
        )
        return user_result_list


def delete_room_from_db(conn, room_id) -> None:
    conn.execute(
        text("DELETE FROM `room` WHERE `room_id`=:room_id"), dict(room_id=room_id)
    )
    return


def delete_user_from_db(conn, room_id, user_id) -> None:
    conn.execute(
        text(
            "DELETE FROM `room_members` WHERE `room_id`=:room_id AND `user_id`=:user_id"
        ),
        dict(room_id=room_id, user_id=user_id),
    )
    return


def change_host(conn, room_id) -> None:
    result = conn.execute(
        text("SELECT `user_id` FROM `room_members` WHERE `room_id`=:room_id"),
        dict(room_id=room_id),
    )
    row = result.first()
    conn.execute(
        text("UPDATE `room` SET `host`=:new_host WHERE `room_id`=:room_id"),
        dict(new_host=row.user_id, room_id=room_id),
    )
    return


def leave_room(room_id: int, token: str) -> None:
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "SELECT `joined_user_count`, `host` FROM `room` WHERE `room_id`=:room_id"
            ),
            dict(room_id=room_id),
        )
        try:
            row = result.one()
            user_id = model.get_user_by_token(token).id
            delete_user_from_db(
                conn, room_id, user_id
            )  # room_members table から /room/leave を呼んだユーザを削除
            if row.joined_user_count == 1:
                delete_room_from_db(conn, room_id)  # room table から roomの情報を削除
            else:
                if row.host == user_id:
                    change_host(conn, room_id)  # room の host を変更
                conn.execute(
                    text(
                        "UPDATE `room` SET `joined_user_count`=:decrement_user_count WHERE `room_id`=:room_id"
                    ),
                    dict(
                        decrement_user_count=(row.joined_user_count - 1),
                        room_id=room_id,
                    ),
                )
            return
        except NoResultFound:
            return  # TODO : エラーハンドリング
