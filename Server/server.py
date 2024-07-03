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
    )  # user_id:[x, y, direction, place_id, color, pen_down, last time played, num of points]

    def get_place_id(user_id: str) -> str:
        try:
            return Place.player_data[user_id][3]
        except KeyError:
            return ""

    def get_place_users(place_id: str) -> list[str]:
        tmp = []

        for user_id in list(Place.player_data.keys()):
            if (
                Place.player_data[user_id][3] == place_id
            ):
                tmp.append(user_id)
        return tmp

    def create_new_user(user_id: str):
        Place.player_data[user_id] = [
            1,  # X
            1,  # Y
            0,  # direction
            "",  # place_id
            "",  # color
            False, # pen down
            0,  # last time played
            0,  # num of points
        ]

    def join(user_id: str, place_id: str, world: int) -> None:
        # create new user
        if user_id not in list(Place.player_data.keys()):
            Place.create_new_user(user_id)

        # create maze if not found
        if place_id not in list(Place.mazes.keys()):
            print("Gen via join")
            Place.gen_place(place_id, Config.default_level, world)
            Place.render(place_id, world)

        # edit the player data
        # x, y, direction, place_id, color, pen_down, last time played, num of points
        Place.player_data[user_id] = [
            random.randint(0, len(Place.pixels[place_id]) - 1),  # X
            random.randint(0, len(Place.pixels[place_id]) - 1),  # Y
            0,  # direction
            place_id,  # place_id
            "",  # color
            False,  # pen down
            time.time(),  # last time played
            Place.player_data[user_id][8],  # num of points
        ]

    def move_player(user_id: str, dir: str) -> None:
        if not user_id in list(Place.player_data.keys()):
            print(f"Playerdata of user {user_id} not found")
            return

        place_id: str = Place.get_place_id(user_id)
        world: int = Place.get_world(user_id)

        data = Place.player_data[user_id].copy()

        if world == -1 or place_id == "":
            return

        rot = data[2]

        if rot == 0:  # up
            if dir == "forward":
                if not Place.pixels[place_id][world][data[0]][data[1] - 1] == "w":
                    Place.player_data[user_id][1] -= 1  # Y

                elif any(
                    [Place.player_data[user_id][0], Place.player_data[user_id][1] - 1]
                    == sublist[1:3]
                    for sublist in Place.keys[place_id][world]
                ):
                    Place.tp_player(
                        user_id,
                        [
                            sublist
                            for sublist in Place.keys[place_id][world]
                            if [
                                Place.player_data[user_id][0],
                                Place.player_data[user_id][1] - 1,
                            ]
                            == sublist[1:3]
                        ][0],
                    )

            elif dir == "backward":
                if not Place.pixels[place_id][world][data[0]][data[1] + 1] == "w":
                    Place.player_data[user_id][1] += 1  # Y

                elif any(
                    [Place.player_data[user_id][0], Place.player_data[user_id][1] + 1]
                    == sublist[1:3]
                    for sublist in Place.keys[place_id][world]
                ):
                    Place.tp_player(
                        user_id,
                        [
                            sublist
                            for sublist in Place.keys[place_id][world]
                            if [
                                Place.player_data[user_id][0],
                                Place.player_data[user_id][1] + 1,
                            ]
                            == sublist[1:3]
                        ][0],
                    )

        elif rot == 1:  # right
            if dir == "forward":
                if not Place.pixels[place_id][world][data[0] + 1][data[1]] == "w":
                    Place.player_data[user_id][0] += 1  # X

                elif any(
                    [Place.player_data[user_id][0] + 1, Place.player_data[user_id][1]]
                    == sublist[1:3]
                    for sublist in Place.keys[place_id][world]
                ):
                    Place.tp_player(
                        user_id,
                        [
                            sublist
                            for sublist in Place.keys[place_id][world]
                            if [
                                Place.player_data[user_id][0] + 1,
                                Place.player_data[user_id][1],
                            ]
                            == sublist[1:3]
                        ][0],
                    )
            elif dir == "backward":
                if not Place.pixels[place_id][world][data[0] - 1][data[1]] == "w":
                    Place.player_data[user_id][0] -= 1  # X

                elif any(
                    [Place.player_data[user_id][0] - 1, Place.player_data[user_id][1]]
                    == sublist[1:3]
                    for sublist in Place.keys[place_id][world]
                ):
                    Place.tp_player(
                        user_id,
                        [
                            sublist
                            for sublist in Place.keys[place_id][world]
                            if [
                                Place.player_data[user_id][0] - 1,
                                Place.player_data[user_id][1],
                            ]
                            == sublist[1:3]
                        ][0],
                    )

        elif rot == 2:  # down
            if dir == "forward":
                if not Place.pixels[place_id][world][data[0]][data[1] + 1] == "w":
                    Place.player_data[user_id][1] += 1  # Y

                elif any(
                    [Place.player_data[user_id][0], Place.player_data[user_id][1] + 1]
                    == sublist[1:3]
                    for sublist in Place.keys[place_id][world]
                ):
                    Place.tp_player(
                        user_id,
                        [
                            sublist
                            for sublist in Place.keys[place_id][world]
                            if [
                                Place.player_data[user_id][0],
                                Place.player_data[user_id][1] + 1,
                            ]
                            == sublist[1:3]
                        ][0],
                    )

            elif dir == "backward":
                if not Place.pixels[place_id][world][data[0]][data[1] - 1] == "w":
                    Place.player_data[user_id][1] -= 1  # Y

                elif any(
                    [Place.player_data[user_id][0], Place.player_data[user_id][1] - 1]
                    == sublist[1:3]
                    for sublist in Place.keys[place_id][world]
                ):
                    Place.tp_player(
                        user_id,
                        [
                            sublist
                            for sublist in Place.keys[place_id][world]
                            if [
                                Place.player_data[user_id][0],
                                Place.player_data[user_id][1] - 1,
                            ]
                            == sublist[1:3]
                        ][0],
                    )

        elif rot == 3:  # left
            if dir == "forward":
                if not Place.pixels[place_id][world][data[0] - 1][data[1]] == "w":
                    Place.player_data[user_id][0] -= 1  # X

                elif any(
                    [Place.player_data[user_id][0] - 1, Place.player_data[user_id][1]]
                    == sublist[1:3]
                    for sublist in Place.keys[place_id][world]
                ):
                    Place.tp_player(
                        user_id,
                        [
                            sublist
                            for sublist in Place.keys[place_id][world]
                            if [
                                Place.player_data[user_id][0] - 1,
                                Place.player_data[user_id][1],
                            ]
                            == sublist[1:3]
                        ][0],
                    )

            elif dir == "backward":
                if not Place.pixels[place_id][world][data[0] + 1][data[1]] == "w":
                    Place.player_data[user_id][0] += 1  # X

                elif any(
                    [Place.player_data[user_id][0] + 1, Place.player_data[user_id][1]]
                    == sublist[1:3]
                    for sublist in Place.keys[place_id][world]
                ):
                    Place.tp_player(
                        user_id,
                        [
                            sublist
                            for sublist in Place.keys[place_id][world]
                            if [
                                Place.player_data[user_id][0] + 1,
                                Place.player_data[user_id][1],
                            ]
                            == sublist[1:3]
                        ][0],
                    )

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
            if not (Place.player_data[user_id][7] + Config.kick_timeout) < cur_time:
                continue

            if Place.player_data[user_id][3] == "" or Place.player_data[user_id][4] == -1:
                continue

            print(f"Kicked {Nicks.get(user_id)} ({user_id})")
            Place.player_data[user_id][3] = ""
            Place.player_data[user_id][4] = ""

    def render(place_id: str) -> None:
        size = len(Place.pixels[place_id])

        if not place_id in list(Place.pixels.keys()):
            Place.pixels[place_id] = []


        pixels = [  # create empty array
            ["000" for _ in range(size)] for _ in range(size)
        ]

        Place.pixels[place_id] = pixels

    def prepare_send(user_id: str, message_id: str) -> str:
        out = []  # _, left, front, right, x, y, dir, team, num_of_points

        place_id = Place.get_place_id(user_id)
        nick = Nicks.get(user_id)

        if place_id == "":
            return

        x = Place.player_data[user_id][0]
        y = Place.player_data[user_id][1]
        dir = Place.player_data[user_id][2]

        team = Place.player_data[user_id][6]
        num_of_points = Place.player_data[user_id][8]

        if x > 0:
            p_left = int(Place.mazes[place_id][world][0][x - 1][y])
        else:
            p_left = 1  # wall

        if x < rp(Place.mazes[place_id][world][2]):
            p_right = int(Place.mazes[place_id][world][0][x + 1][y])
        else:
            p_right = 1  # wall

        if y > 0:
            p_up = int(Place.mazes[place_id][world][0][x][y - 1])
        else:
            p_up = 1  # wall

        if y < rp(Place.mazes[place_id][world][2]):
            p_down = int(Place.mazes[place_id][world][0][x][y + 1])
        else:
            p_down = 1  # wall

        sens = 0

        if dir == 0:  # facing up
            sens += 1 * p_up
            sens += 2 * p_right
            sens += 4 * p_down
            sens += 8 * p_left
        elif dir == 1:  # facing right
            sens += 1 * p_right
            sens += 2 * p_down
            sens += 4 * p_left
            sens += 8 * p_up
        elif dir == 2:  # facing down
            sens += 1 * p_down
            sens += 2 * p_left
            sens += 4 * p_right
            sens += 8 * p_up
        elif dir == 3:  # facing left
            sens += 1 * p_left
            sens += 2 * p_up
            sens += 4 * p_right
            sens += 8 * p_down

        min_distance = float("inf")
        closest_key = None

        for key in [sublist[1:3] for sublist in Place.keys[place_id][world]]:
            x_k, y_k = key
            dist = math.sqrt((x_k - x) ** 2 + (y_k - y) ** 2)
            if dist < min_distance:
                min_distance = dist
                closest_key = key

        x_key, y_key = closest_key

        min_distance = float("inf")
        closest_point = None

        for point in [sublist[:2] for sublist in Place.points[place_id][world]]:
            x_p, y_p = point
            dist = math.sqrt((x_p - x) ** 2 + (y_p - y) ** 2)
            if dist < min_distance:
                min_distance = dist
                closest_point = key

        x_point, y_point = closest_point

        #        8      1     1   1      1         1        1       1      1     1      = 17/22
        # <id> <nick> <size> <x> <y> <x_point> <y_point> <x_key> <y_key> <dir> <sens>

        out.append("_r_")  # random string so i can handle it differently

        out.append(str(message_id))  # id
        out.append(str(nick))  # nick
        out.append(str(rp(Place.mazes[place_id][world][2])))  # size
        out.append(str(x))  # x
        out.append(str(y))  # y

        out.append(str(x_point))  # x_point
        out.append(str(y_point))  # y_point

        out.append(str(x_key))  # x_key
        out.append(str(y_key))  # y_key

        out.append(str(dir))  # dir

        out.append(str(sens))  # sens

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
        for file in Save.files:
            if not os.path.exists(f"{Save.folder}{file}{Save.extension}"):
                continue
            cur_time = datetime.now().strftime("%d-%m-%y-%H-%M-%S-")
            os.rename(
                f"{Save.folder}{file}{Save.extension}",
                f"{Save.folder}{cur_time}{file}{Save.extension}",
            )

        Save.save_mazes()
        Save.save_players()

    def save_mazes():
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
        Save.load_mazes()
        Save.load_players()

    def load_mazes():
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
                    len(world_data[0]) == rp(world_data[2])
                    or len(world_data[0][0]) == rp(world_data[2])
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
            data:list
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

                    resp.append(place_id)

                    resp.append(str(len(Place.pixels[place_id])))  # size

                    for r in Place.pixels[place_id]:
                        row = ",".join(r.split())
                        resp.append(row)


                    for user_id in Place.get_place_users(place_id):
                        data = Place.player_data[user_id]
                        # usr;[user_id];[nick];[x];[y];[dir][color];[team];[collected_points]
                        resp.append(
                            f"usr;{user_id};{Nicks.get(user_id)};{data[0]};{data[1]};{data[2]};{data[5]};{data[6]};{data[8]}"
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

    Save.init()
    Save.create_backup()
    Save.load_all()

    if not Config.public_server in list(Place.mazes.keys()):
        Place.gen_place(Config.public_server, Config.default_size)
        Place.render(Config.public_server)

    Server.edit_script()

    bg_t = threading.Thread(target=Server.background_func)
    bg_t.start()

    loop = threading.Thread(target=Server.loop)
    loop.start()

    start_server = websockets.serve(WS.handler, "0.0.0.0", WS.port)
    asyncio.get_event_loop().run_until_complete(start_server)
    asyncio.get_event_loop().run_forever()
