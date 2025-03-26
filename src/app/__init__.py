import eventlet
import os
from flask import Flask
from flask_socketio import SocketIO

eventlet.monkey_patch()
# 指定 static_folder 为根目录下的 "static"
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
app = Flask(
    __name__, static_folder=os.path.join(project_root, "static"), static_url_path=""
)
app.config["SECRET_KEY"] = "your_secret_key"
socketio = SocketIO(app)

# 导入路由和游戏逻辑模块
from app import routes, game

# 启动游戏主循环任务
socketio.start_background_task(game.game_loop)
