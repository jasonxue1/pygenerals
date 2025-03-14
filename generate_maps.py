import os
import random


def generate_map(width=30, height=30):
    """
    生成一个地图，其中：
    - 地图边界（最外圈）全部为山（1）
    - 地图内部 5% 为塔（2）
    - 地图内部 20% 为山（1）
    - 剩下为空地（0）
    """
    grid = []
    for y in range(height):
        row = []
        for x in range(width):
            # 如果在边界上，则设为山（1）
            if x == 0 or x == width - 1 or y == 0 or y == height - 1:
                row.append("1")
            else:
                r = random.random()
                if r < 0.05:
                    row.append("2")  # 塔
                elif r < 0.05 + 0.20:
                    row.append("1")  # 山
                else:
                    row.append("0")  # 空地
        # 将行列表拼成字符串
        grid.append("".join(row))
    # 将行用换行符拼接
    return "\n".join(grid)


def get_next_map_filename(maps_dir) -> str:
    existing = []
    for filename in os.listdir(maps_dir):
        if filename.endswith(".map"):
            try:
                num = int(os.path.splitext(filename)[0])
                existing.append(num)
            except ValueError:
                continue
    next_num = max(existing) + 1 if existing else 1
    return os.path.join(maps_dir, f"{next_num}.map")


def main():
    maps_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "maps")
    if not os.path.exists(maps_dir):
        os.makedirs(maps_dir)
    map_content = generate_map()
    map_filename = get_next_map_filename(maps_dir)
    with open(map_filename, "w") as f:
        f.write(map_content)
    print(f"Generated new map: {map_filename}")


if __name__ == "__main__":
    main()
