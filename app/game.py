import os
import random
import threading
from app import socketio


# 全局游戏状态
game_state = {
    "turn": 0,
    "cells": [],
    "width": 0,
    "height": 0,
    "running": True,
    "lock": threading.Lock(),
}

# pending_moves 用于存储同一 cell 在本步内额外发出的移动命令
pending_moves = {}


def load_random_map():
    """
    从项目根目录下的 maps 文件夹中随机选择一个 .map 文件，
    读取文件内容并转换为二维整数数组。
    """
    # 项目根目录
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    maps_dir = os.path.join(project_root, "maps")
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
            if cell_type == 2:
                init_army = random.randint(40, 50)
            else:
                init_army = 0
            cell = {
                "type": cell_type,  # 0: 空地, 1: 山, 2: 塔
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


init_game()


def process_move(username, frm, direction):
    """
    根据 WASD 移动规则处理一次移动请求。
    每次移动将发起 cell 中所有兵力（除留 1 防守）转移到目标 cell，
    目标为塔（且未被占领）时采用两两抵消规则。
    返回 True 表示移动成功，否则 False。
    """
    r_from, c_from = frm
    if not (0 <= r_from < game_state["height"] and 0 <= c_from < game_state["width"]):
        return False
    cell_from = game_state["cells"][r_from][c_from]
    if cell_from["army"] <= 1:
        return False
    # 计算移动兵力
    moving_army = cell_from["army"] - 1
    cell_from["army"] = 1
    cell_from["moved"] = True

    # 根据方向计算目标坐标
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
        return False
    cell_to = game_state["cells"][r_to][c_to]
    # 山不可通行
    if cell_to["type"] == 1:
        return False

    # 处理目标 cell
    if cell_to["type"] == 2 and cell_to["owner"] is None:
        if moving_army > cell_to["army"]:
            new_army = moving_army - cell_to["army"]
            cell_to["owner"] = username
            cell_to["army"] = max(1, new_army)
        else:
            cell_to["army"] -= moving_army
            if cell_to["army"] < 0:
                cell_to["army"] = 0
    else:
        if cell_to["owner"] is None:
            cell_to["owner"] = username
            cell_to["army"] = moving_army
            cell_to["is_home"] = False
        elif cell_to["owner"] == username:
            cell_to["army"] += moving_army
        else:
            return False
    return True


def broadcast_state():
    state_for_client = {
        "turn": game_state["turn"],
        "width": game_state["width"],
        "height": game_state["height"],
        "cells": game_state["cells"],
    }
    socketio.emit("state", state_for_client)


def game_loop():
    # 每步 1 秒（即每秒 1 步）
    while game_state["running"]:
        socketio.sleep(1)
        with game_state["lock"]:
            # 重置所有 cell 的 moved 标记（新步开始）
            for r in range(game_state["height"]):
                for c in range(game_state["width"]):
                    game_state["cells"][r][c]["moved"] = False
            # 处理 pending moves
            for key in list(pending_moves.keys()):
                move_cmd = pending_moves.pop(key)
                username_pending = move_cmd["username"]
                frm_pending = move_cmd["from"]
                direction_pending = move_cmd["direction"]
                r_from, c_from = frm_pending
                cell_from = game_state["cells"][r_from][c_from]
                if cell_from["owner"] == username_pending and not cell_from["moved"]:
                    process_move(username_pending, frm_pending, direction_pending)
            # 更新回合，并为每个家和占领塔增加兵力
            game_state["turn"] += 1
            for r in range(game_state["height"]):
                for c in range(game_state["width"]):
                    cell = game_state["cells"][r][c]
                    if cell["owner"] is not None and (
                        cell["is_home"] or cell["type"] == 2
                    ):
                        cell["army"] += 1
            broadcast_state()

            if game_state["turn"] % 25 == 0:
                for r in range(game_state["height"]):
                    for c in range(game_state["width"]):
                        cell = game_state["cells"][r][c]
                        if cell["owner"] is not None:
                            cell["army"] += 1
