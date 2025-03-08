import eventlet
import os
import random
import threading
from flask import Flask, jsonify
from flask_socketio import SocketIO, join_room

eventlet.monkey_patch()
app = Flask(__name__, static_folder="static", static_url_path="")
app.config["SECRET_KEY"] = "your_secret_key"
socketio = SocketIO(app)

# 全局游戏状态：
# cells：二维数组，每个 cell 为字典，包含：
#   "type": int      (0: 空地, 1: 山, 3: 塔)
#   "owner": str or None
#   "army": int      当前兵力
#   "is_home": bool  是否为家（初始出生地）
#   "moved": bool    本 step 是否已移动过
game_state = {
    "turn": 0,
    "cells": [],
    "width": 0,
    "height": 0,
    "running": False,
    "lock": threading.Lock(),
}


def load_random_map():
    """
    从根目录下 maps 文件夹中随机选择一个 .map 文件，
    读取文件内容并转换为二维整数数组。
    """
    maps_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps")
    map_files = [f for f in os.listdir(maps_dir) if f.endswith(".map")]
    if not map_files:
        raise Exception("No map files found in maps directory.")
    chosen_file = random.choice(map_files)
    map_path = os.path.join(maps_dir, chosen_file)
    with open(map_path, "r") as f:
        lines = f.read().strip().splitlines()
    grid = []
    for line in lines:
        row = [int(ch) for ch in line.strip()]
        grid.append(row)
    return grid


def init_game():
    grid = load_random_map()
    height = len(grid)
    width = len(grid[0]) if height > 0 else 0
    cells = []
    for r in range(height):
        row = []
        for c in range(width):
            cell_type = grid[r][c]
            # 如果 cell 为塔，则初始兵力随机在 40～50 之间（未被占领时）
            if cell_type == 3:
                init_army = random.randint(40, 50)
            else:
                init_army = 0
            cell = {
                "type": cell_type,  # 0: 空地, 1: 山, 3: 塔
                "owner": None,
                "army": init_army,
                "is_home": False,
                "moved": False,
            }
            row.append(cell)
        cells.append(row)
    game_state["cells"] = cells
    game_state["height"] = height
    game_state["width"] = width
    game_state["turn"] = 0
    game_state["running"] = True


init_game()


def game_loop():
    # 每 step 0.5 秒（即每秒 2 个 step）
    while game_state["running"]:
        socketio.sleep(0.5)
        with game_state["lock"]:
            game_state["turn"] += 1
            for r in range(game_state["height"]):
                for c in range(game_state["width"]):
                    cell = game_state["cells"][r][c]
                    # 家和已占领的塔每 step 增加 1 兵力
                    if cell["owner"] is not None and (
                        cell["is_home"] or cell["type"] == 3
                    ):
                        cell["army"] += 1
                    # 重置每个 cell 的移动标记
                    cell["moved"] = False
            broadcast_state()


def broadcast_state():
    state_for_client = {
        "turn": game_state["turn"],
        "width": game_state["width"],
        "height": game_state["height"],
        "cells": game_state["cells"],
    }
    socketio.emit("state", state_for_client)


@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/map")
def get_map():
    return jsonify({"cells": game_state["cells"]})


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
    系统在随机一个空地上生成其“家”：
      - 家初始兵力为 1
      - 标记 is_home 为 True
    """
    username = data.get("username")
    room = data.get("room")
    if not username or not room:
        return
    join_room(room)
    with game_state["lock"]:
        # 寻找所有空地（仅限 type==0 且未被占领）
        empty_cells = []
        for r in range(game_state["height"]):
            for c in range(game_state["width"]):
                cell = game_state["cells"][r][c]
                if cell["type"] == 0 and cell["owner"] is None:
                    empty_cells.append((r, c))
        if not empty_cells:
            return
        spawn = random.choice(empty_cells)
        r, c = spawn
        cell = game_state["cells"][r][c]
        cell["owner"] = username
        cell["army"] = 1  # 家初始兵力为 1
        cell["is_home"] = True
    print(f"{username} joined and spawned at {spawn}")
    broadcast_state()


@socketio.on("move")
def handle_move(data):
    """
    处理移动请求：
    data 格式 { "username": str, "from": [r, c], "direction": str }
    移动要求：
      - 发起移动的 cell 兵力必须大于 2，否则移动失败
      - 发起移动时，从该 cell 扣除 1 兵力，并标记该 cell 本 step 已移动
      - 计算目标坐标（w:上, a:左, s:下, p:右）
      - 山（type==1）不可通行
      - 如果目标为塔且未被占领，进行两两抵消：每次移动扣除目标塔 1 兵，
        若目标塔兵力降至 0或以下，则该塔归属移动方，兵力设为 1
      - 否则：若目标未被占领，则占领并兵力置为 1；若目标已为己方，则兵力加 1
    """
    username = data.get("username")
    frm = data.get("from")
    direction = data.get("direction")
    if not username or frm is None or not direction:
        return
    with game_state["lock"]:
        r_from, c_from = frm
        if not (
            0 <= r_from < game_state["height"] and 0 <= c_from < game_state["width"]
        ):
            return
        cell_from = game_state["cells"][r_from][c_from]
        # 必须为自己的 cell 且本 step 未移动过
        if cell_from["owner"] != username or cell_from["moved"]:
            return
        # 只有兵力大于 2 才能移动
        if cell_from["army"] <= 2:
            return
        # 扣除 1 兵，并标记已移动
        cell_from["army"] -= 1
        cell_from["moved"] = True

        # 计算目标坐标
        dr, dc = 0, 0
        if direction == "w":
            dr = -1
        elif direction == "a":
            dc = -1
        elif direction == "s":
            dr = 1
        elif direction == "d":
            dc = 1
        r_to = r_from + dr
        c_to = c_from + dc
        if not (0 <= r_to < game_state["height"] and 0 <= c_to < game_state["width"]):
            return
        cell_to = game_state["cells"][r_to][c_to]
        # 山不可通行
        if cell_to["type"] == 1:
            return

        # 如果目标为塔且未被占领，进行两两抵消
        if cell_to["type"] == 3 and cell_to["owner"] is None:
            if cell_to["army"] > 0:
                cell_to["army"] -= 1
                if cell_to["army"] <= 0:
                    cell_to["owner"] = username
                    cell_to["army"] = 1
        else:
            # 非塔或已占领塔、空地：若目标未被占领，则占领并兵力置为 1；若己方，则兵力加 1
            if cell_to["owner"] is None:
                cell_to["owner"] = username
                cell_to["army"] = 1
                cell_to["is_home"] = False
            elif cell_to["owner"] == username:
                cell_to["army"] += 1
            # 若目标为敌方占领，则不做移动（或可扩展战斗逻辑）
    broadcast_state()


socketio.start_background_task(game_loop)
