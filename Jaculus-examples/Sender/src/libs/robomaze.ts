/**
* A lib for sending data to robomaze (https://github.com/C2Coder/RoboMaze)
*/

import * as radio from "simpleradio"

export function create_cb(_func) {
    radio.on("keyvalue", (key, value, info) => {
        _func(value, key);
    })
}

export function begin(_group: number) {
    radio.begin(_group);
}

export function send(_cmd: string, _message_id:number) {
    radio.sendString(`${_cmd} ${_message_id}`)
}