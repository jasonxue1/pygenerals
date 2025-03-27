import random
from flask import jsonify
from flask_socketio import join_room
from app import app, socketio
from app import game


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/map")
def get_map():
    return jsonify({"cells": game.game_state["cells"]})


@socketio.on("connect")
def on_connect():
    print("A client connected.")


@socketio.on("disconnect")
def on_disconnect():
    print("A client disconnected.")


@socketio.on("join")
def handle_join(data):
    """
    玩家发送 { "username": str, "room": str } 加入游戏，
    如果该玩家还没有家，则在随机空地上生成其家：
      - 初始兵力为 1
      - 标记 is_home 为 True
    """
    username = data.get("username")
    room = data.get("room")
    if not username or not room:
        return
    join_room(room)
    with game.game_state["lock"]:
        # 检查该玩家是否已有家
        home_exists = False
        for r in range(game.game_state["height"]):
            for c in range(game.game_state["width"]):
                cell = game.game_state["cells"][r][c]
                if cell["owner"] == username and cell["is_home"]:
                    home_exists = True
                    break
            if home_exists:
                break
        if not home_exists:
            empty_cells = []
            for r in range(game.game_state["height"]):
                for c in range(game.game_state["width"]):
                    cell = game.game_state["cells"][r][c]
                    if cell["type"] == 0 and cell["owner"] is None:
                        empty_cells.append((r, c))
            if not empty_cells:
                return
            spawn = random.choice(empty_cells)
            r, c = spawn
            cell = game.game_state["cells"][r][c]
            cell["owner"] = username
            cell["army"] = 1
            cell["is_home"] = True
    print(f"{username} joined")
    game.broadcast_state()


@socketio.on("move")
def handle_move(data):
    """
    处理移动请求：
    data 格式 { "username": str, "from": [r, c], "direction": str }
    """
    username = data.get("username")
    frm = data.get("from")
    direction = data.get("direction")
    if not username or frm is None or not direction:
        return
    with game.game_state["lock"]:
        r_from, c_from = frm
        if not (
            0 <= r_from < game.game_state["height"]
            and 0 <= c_from < game.game_state["width"]
        ):
            return
        cell_from = game.game_state["cells"][r_from][c_from]
        if cell_from["owner"] != username:
            return
        if not cell_from["moved"]:
            game.process_move(username, frm, direction)
        else:
            key = (username, r_from, c_from)
            game.pending_moves[key] = {
                "username": username,
                "from": frm,
                "direction": direction,
            }
    game.broadcast_state()
