import os
import toml
from app import app, socketio

# 读取根目录下的配置文件 config.toml
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.toml")
config = toml.load(config_path)
ip = config["server"]["ip"]
port = config["server"]["port"]

if __name__ == "__main__":
    socketio.run(app, host=ip, port=port, debug=True)
