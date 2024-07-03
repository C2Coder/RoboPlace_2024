#!/bin/python3
from flask import Flask, request
from flask_cors import CORS
import socket
import numpy as np
import random
import os
import threading
import time
import websockets
import asyncio
import hashlib
import math
from datetime import datetime


class Config:
    use_proxy = False
    proxy_address = "hotncold.ddns.net"

    default_size = 100

    public_server = "Robo"
    dgkops = True  # Dynamicaly Gen Keys On Public Server

    kick_timeout = 10 * 60  # 10 minutes (600 secs)
    # kick_timeout = 5*60  # 5 minutes  (300 secs)
    # kick_timeout = 1 * 60  # 1 minute (60 secs)
    # kick_timeout = 10  # (10 secs)


class Colors:

    def hex_to_rgb(hex_color):
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))

    def rgb_to_hex(rgb_color):
        return "#{:02x}{:02x}{:02x}".format(*rgb_color)


class Place:
    pixels = {}  # place_id:[[]]
    player_data = (
        {}
    )  # user_id:[x, y, direction, place_id, color, pen_down, last time played, num of points, moved?]

    def get_place_id(user_id: str) -> str:
        try:
            return Place.player_data[user_id][3]
        except KeyError:
            return ""

    def get_place_users(place_id: str) -> list[str]:
        tmp = []

        for user_id in list(Place.player_data.keys()):
            if Place.player_data[user_id][3] == place_id:
                tmp.append(user_id)
        return tmp

    def get_place_size(place_id: str) -> int:
        return len(Place.pixels[place_id])

    def create_place(place_id: str, size: int):
        Place.pixels[place_id] = []

        for _ in range(size):
            Place.pixels[place_id].append(["fff" for _ in range(size)])

    def create_new_user(user_id: str):
        Place.player_data[user_id] = [
            1,  # X
            1,  # Y
            0,  # direction
            "",  # place_id
            "f00",  # color
            False,  # pen down
            0,  # last time played
            0,  # num of points
            False,  # moved?
        ]

    def join(user_id: str, place_id: str) -> None:
        # create new user
        if user_id not in list(Place.player_data.keys()):
            Place.create_new_user(user_id)

        # create maze if not found
        if place_id not in list(Place.pixels.keys()):
            print("Gen via join")
            Place.create_place(place_id, Config.default_size)

        # edit the player data
        # x, y, direction, place_id, color, pen_down, last time played, num of points, moved?
        Place.player_data[user_id] = [
            random.randint(0, len(Place.pixels[place_id]) - 1),  # X
            random.randint(0, len(Place.pixels[place_id]) - 1),  # Y
            0,  # direction
            place_id,  # place_id
            Place.player_data[user_id][4],  # color
            False,  # pen down
            time.time(),  # last time played
            Place.player_data[user_id][8],  # num of points
            False,  # moved
        ]

    def move_player(user_id: str, dir: str) -> None:
        if not user_id in list(Place.player_data.keys()):
            print(f"Playerdata of user {user_id} not found")
            return

        place_id: str = Place.get_place_id(user_id)
        print(user_id)
        print(place_id)
        place_size: int = Place.get_place_size(place_id)

        if place_id == "":
            return

        rot = Place.player_data[user_id][2]

        # up, right, down, left
        dirs = [(0, -1), (1, 0), (0, 1), (-1, 0)]

        if dir == "forward":
            tmp_x = Place.player_data[user_id][0] + dirs[rot][0]
            tmp_y = Place.player_data[user_id][1] + dirs[rot][1]

        elif dir == "backward":
            tmp_x = Place.player_data[user_id][0] - dirs[rot][0]
            tmp_y = Place.player_data[user_id][1] - dirs[rot][1]

        if tmp_x < 0 or tmp_x >= place_size:
            Place.player_data[user_id][8] = False
            return

        if tmp_y < 0 or tmp_y >= place_size:
            Place.player_data[user_id][8] = False
            return

        Place.player_data[user_id][8] = True
        if Place.player_data[user_id][5]:
            Place.pixels[place_id][Place.player_data[user_id][1]][Place.player_data[user_id][0]] = Place.player_data[user_id][4]

        Place.player_data[user_id][0] = tmp_x
        Place.player_data[user_id][1] = tmp_y

    def rotate_player(user_id: str, dir: str) -> None:
        if not user_id in list(Place.player_data.keys()):
            print(f"Playerdata of user {user_id} not found")
            return
        if dir == "left":
            Place.player_data[user_id][2] -= 1
        elif dir == "right":
            Place.player_data[user_id][2] += 1

        if Place.player_data[user_id][2] < 0:
            Place.player_data[user_id][2] = 3
        elif Place.player_data[user_id][2] > 3:
            Place.player_data[user_id][2] = 0

    def kick_not_playing() -> None:

        cur_time = time.time()

        for user_id in list(Place.player_data.keys()):
            if not (Place.player_data[user_id][6] + Config.kick_timeout) < cur_time:
                continue

            if (
                Place.player_data[user_id][3] == ""
            ):
                continue

            print(f"Kicked {Nicks.get(user_id)} ({user_id})")
            Place.player_data[user_id][3] = ""

    def prepare_send(user_id: str, message_id: str) -> str:
        out = []  # _, x, y, dir, did_move, color, pen_down, num_of_points

        # user_id:[x, y, direction, place_id, color, pen_down, last time played, num of points, moved?]

        place_id = Place.get_place_id(user_id)
        nick = Nicks.get(user_id)

        if place_id == "":
            ""
        (
            x,
            y,
            direction,
            place_id,
            color,
            pen_down,
            last_time_played,
            num_of_points,
            moved,
        ) = Place.player_data[user_id]

        #        8     1   1    1      3         1        1     = 16/22
        # <id> <nick> <x> <y> <dir> <color> <pen_down> <moved>

        out.append("_r_")  # random string so i can handle it differently

        out.append(str(message_id))  # id
        out.append(str(nick))  # nick
        out.append(str(x))  # x
        out.append(str(y))  # y

        out.append(str(direction))  # dir

        out.append(str(color))  # color
        out.append("1" if pen_down else "0")  # pen_down
        out.append("1" if moved else "0")  # moved

        return " ".join(out)


class Logger:
    logs = []
    file = "logs/logs.txt"
    use = True

    def init():
        if not Logger.use:
            return
        if not os.path.isfile(Logger.file):
            with open(Logger.file, "w") as f:
                f.write("")

    def log(msg):
        if not Logger.use:
            return
        Logger.logs.append(msg)

    def save_logs():
        if not Logger.use:
            return
        with open(Logger.file, "a") as f:
            for log in Logger.logs:
                f.write(f"{log}\n")
            Logger.logs = []


class Save:
    folder = "save/"
    backup_folder = "backups/"

    extension = ".save"
    files = ["places"]

    backup_interval = 15 * 60  # 15 minutes
    last_backup = 0

    def init():
        if not Save.folder.replace("/", "") in os.listdir():
            os.mkdir(Save.folder)

        if not Save.backup_folder.replace("/", "") in os.listdir():
            os.mkdir(Save.backup_folder)

        files = os.listdir("save")
        for file in Save.files:
            if not file.replace(Save.extension, "") in files:
                with open(f"{Save.folder}{file}{Save.extension}", "w+") as f:
                    f.write("")

    def create_backup():
        Save.last_backup = time.time()

        for file in os.listdir("save"):
            if not file.replace(Save.extension, "") in Save.files:
                os.system(f"rm {Save.folder}{file}")

        for file in Save.files:
            if not os.path.exists(f"{Save.folder}{file}{Save.extension}"):
                continue
            cur_time = datetime.now().strftime("%d-%m-%y-%H-%M-%S-")
            os.system(
                f"cp {Save.folder}{file}{Save.extension} {Save.backup_folder}{cur_time}{file}{Save.extension}"
            )

    def save_all():
        return
        for file in Save.files:
            if not os.path.exists(f"{Save.folder}{file}{Save.extension}"):
                continue
            cur_time = datetime.now().strftime("%d-%m-%y-%H-%M-%S-")
            os.rename(
                f"{Save.folder}{file}{Save.extension}",
                f"{Save.folder}{cur_time}{file}{Save.extension}",
            )

        Save.save_places()

    def save_places():
        tmp = []
        for place_id in list(Place.mazes.keys()):
            tmp.append(f"{place_id}:")
            for world, data in enumerate(Place.mazes[place_id]):
                if data == []:
                    continue
                tmp.append(f"{' '*2}world-{world}:")
                tmp.append(f"{' '*4}maze:")
                for row in data[0]:
                    _tmp = ""
                    for c in row:
                        _tmp += "#" if int(c) else " "
                    tmp.append(f"{' '*6}{_tmp}")

                tmp.append(f"{' '*4}points pos:")
                _tmp = ""
                if place_id in list(Place.points.keys()):
                    for p in Place.points[place_id][world]:
                        _tmp += f"({p[0]}, {p[1]});"
                tmp.append(f"{' '*6}{_tmp.rstrip(';')}")

                tmp.append(f"{' '*4}keys pos:")
                _tmp = ""
                if place_id in list(Place.keys.keys()):
                    for p in Place.keys[place_id][world]:
                        _tmp += f"({p[0]}, {p[1]}, {p[2]}, {p[3]}, {p[4]}, {p[5]});"
                tmp.append(f"{' '*6}{_tmp.rstrip(';')}")

                tmp.append(f"{' '*4}lvl:")
                tmp.append(f"{' '*6}{data[1]}")

                tmp.append(f"{' '*4}size:")
                tmp.append(f"{' '*6}{data[2]}")

                tmp.append(f"{' '*4}collected points:")
                tmp.append(f"{' '*6}{data[3]}")

        with open(f"{Save.folder}mazes.save", "x") as f:
            for line in tmp:
                f.write(line + "\n")

    def load_all():
        for file in Save.files:
            if not os.path.exists(f"{Save.folder}{file}{Save.extension}"):
                return
        Save.load_places()

    def load_places():
        with open(f"{Save.folder}mazes.save", "r") as f:
            lines = [line.replace("\n", "") for line in f.readlines()]

        i = 0
        worlds = {}
        place_id = ""
        world = 0
        while i < len(lines) - 1:
            if lines[i].count(" ") == 0:
                place_id = lines[i].rstrip(":")
                worlds[place_id] = []

            elif "world-" in lines[i]:
                world = int(lines[i].replace("world-", "").replace(":", ""))
                while len(worlds[place_id]) <= world:
                    worlds[place_id].append([])

                tmp_maze = []
                o = int(i + 2)
                while o < len(lines) - 1:
                    if "points pos:" in lines[o]:
                        break
                    tmp_maze.append(
                        lines[o].strip().replace("#", "1").replace(" ", "0")
                    )
                    o += 1

                worlds[place_id][world].append(
                    [[int(n) for n in inner_list] for inner_list in tmp_maze]
                )
                i = int(o - 1)
            elif "points pos:" in lines[i]:
                i += 1
                if not place_id in list(Place.points.keys()):
                    Place.points[place_id] = []

                while len(Place.points[place_id]) <= world:
                    Place.points[place_id].append([])

                Place.points[place_id][world] = []

                for p in (
                    lines[i]
                    .replace(" ", "")
                    .replace(")", "")
                    .replace("(", "")
                    .split(";")
                ):
                    Place.points[place_id][world].append([int(n) for n in p.split(",")])
            elif "keys pos:" in lines[i]:
                i += 1
                if not place_id in list(Place.keys.keys()):
                    Place.keys[place_id] = []

                while len(Place.keys[place_id]) <= world:
                    Place.keys[place_id].append([])

                Place.keys[place_id][world] = []

                for p in (
                    lines[i]
                    .replace(" ", "")
                    .replace(")", "")
                    .replace("(", "")
                    .split(";")
                ):
                    Place.keys[place_id][world].append([int(n) for n in p.split(",")])
            elif "lvl:" in lines[i]:
                i += 1
                worlds[place_id][world].append(int(lines[i].replace(" ", "")))
            elif "size:" in lines[i]:
                i += 1
                worlds[place_id][world].append(int(lines[i].replace(" ", "")))
            elif "collected points:" in lines[i]:
                i += 1
                worlds[place_id][world].append(int(lines[i].replace(" ", "")))
            i += 1

        for place_id in list(worlds.keys()):
            Place.mazes[place_id] = []

            for world, world_data in enumerate(worlds[place_id]):
                if world_data == []:
                    Place.mazes[place_id].append(world_data)
                    continue

                if not (
                    len(world_data[0]) == world_data[2]
                    or len(world_data[0][0]) == world_data[2]
                ):
                    print(f"Wrong size in maze:{place_id} in world:{world}")
                    continue
                elif not Place.calc_lvl_size(int(world_data[1])) == int(world_data[2]):
                    print(f"Wrong lvl in maze:{place_id} in world:{world}")
                    continue
                Place.mazes[place_id].append(world_data)


class Nicks:
    nicks = {}

    def get(user_id: str) -> str:
        if user_id in list(Nicks.nicks.keys()):
            return Nicks.nicks[user_id]
        return user_id

    def get_user(nick: str) -> str:
        for key, val in list(Nicks.nicks.items()):
            if val == nick:
                return key

    def set(user_id: str, nick: str) -> None:
        Nicks.nicks[user_id] = nick


class Server:
    port = 8888
    proxy_port = 8080

    def has_numbers(inputString):
        return any(char.isdigit() for char in inputString)

    def getIp() -> str:
        return "127.0.0.1"
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        return str(s.getsockname()[0])

    if Config.use_proxy:
        local_ip = Config.proxy_address

    local_ip = getIp()

    def loop() -> None:
        app.static_folder = "static"
        app.run(host="0.0.0.0", port=Server.port, debug=False)

    def background_func() -> None:
        while True:
            time.sleep(60)  # 1 min (60 secs)
            Place.kick_not_playing()
            Logger.save_logs()

            if Save.backup_interval + Save.last_backup < time.time():
                Save.create_backup()
            else:
                Save.save_all()

    def edit_script() -> None:
        with open("static/script.js", "r") as file:
            lines = file.readlines()

        lines[0] = f"server_ip = '{Server.local_ip}';\n"
        lines[1] = f"http_port = {Server.port};\n"
        lines[2] = f"ws_port = {WS.port};\n"

        lines[3] = f"proxy_server_ip = '{Config.proxy_address}';\n"
        lines[4] = f"proxy_http_port = {Server.proxy_port};\n"
        lines[5] = f"proxy_ws_port = {WS.proxy_port};\n"

        lines[6] = f"update_interval = {1000};\n"

        with open("static/script.js", "w") as file:
            file.writelines(lines)

    def handle_cmd(data_in) -> str:
        try:
            data: list
            data = data_in.strip().split()
            # data = ["serial", "c2c", "move", "forward", "01"]
            user_id = data[0]
            nick = data[1]
            cmd = data[2]
            message_id = data[-1]

            if (not user_id in list(Place.player_data.keys())) and cmd != "join":
                print(f"Playerdata of user {user_id} not found")
                return ""

            Nicks.set(user_id, nick)

            if cmd == "join":
                if len(data) == 4:
                    Place.join(user_id, Config.public_server)
                else:
                    Place.join(user_id, data[3])

            elif cmd == "move":
                dir = data[3]
                Place.move_player(user_id, dir)

            elif cmd == "rotate":
                dir = data[3]
                Place.rotate_player(user_id, dir)

            elif cmd == "pen":
                if data[3] == "up":
                    Place.player_data[user_id][5] = False
                elif data[3] == "down":
                    Place.player_data[user_id][5] = True
            
            elif cmd == "color":
                if len(data[3]) == 3:
                    Place.player_data[user_id][4] = data[3]

            Logger.log(" ".join(data))

            Place.player_data[user_id][6] = time.time()

            return Place.prepare_send(user_id, message_id)

        except KeyboardInterrupt:
            exit()


class WS:
    port = 8001
    proxy_port = port

    async def handler(websocket, path) -> None:
        while True:
            try:
                data = await websocket.recv()
                print(data)
                toks = data.split(" ")

                if toks[0] == "ping":
                    await websocket.send("pong")
                    continue

                if toks[0] == "get_pixels":
                    if toks[1] in list(Place.player_data.keys()):
                        user_id = toks[1]
                    elif toks[1] in list(Nicks.nicks.values()):
                        user_id = Nicks.get_user(toks[1])
                    else:
                        await websocket.send("error\nwrong_nick")
                        continue

                    place_id = Place.get_place_id(user_id)

                    if not place_id in list(Place.pixels.keys()):
                        await websocket.send("error\nwrong_place_id")
                        continue

                    resp = []

                    resp.append(str(place_id))

                    resp.append(str(len(Place.pixels[place_id])))  # size

                    for r in Place.pixels[place_id]:
                        row = "".join(r)
                        resp.append(str(row))

                    for user_id in Place.get_place_users(place_id):
                        data = Place.player_data[user_id]
                        # [x, y, direction, place_id, color, pen_down, last time played, num of points, moved?]
                        # usr;[user_id];[nick];[x];[y];[dir][color]
                        resp.append(
                            f"usr;{user_id};{Nicks.get(user_id)};{data[0]};{data[1]};{data[2]};{data[4]}"
                        )

                    await websocket.send("\n".join(resp).strip("\n"))
                    continue

                resp = Server.handle_cmd(data)
                if resp != "":
                    print(resp)
                    await websocket.send(resp)

            except KeyboardInterrupt:
                exit()
            # dont care about exceptions, please dont kill me :)
            except websockets.exceptions.ConnectionClosedOK:
                return
            except websockets.exceptions.ConnectionClosedError:
                return
            except websockets.exceptions.ConnectionClosed:
                return


app = Flask(__name__)
CORS(app)


@app.route("/", methods=["GET"])
def main_page() -> str:
    with open("static/index.htm") as index_file:
        return index_file.read()


if __name__ == "__main__":
    Logger.init()

    # Save.init()
    # Save.create_backup()
    # Save.load_all()

    if not Config.public_server in list(Place.pixels.keys()):
        Place.create_place(Config.public_server, Config.default_size)

    Server.edit_script()

    bg_t = threading.Thread(target=Server.background_func)
    bg_t.start()

    loop = threading.Thread(target=Server.loop)
    loop.start()

    start_server = websockets.serve(WS.handler, "0.0.0.0", WS.port)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
