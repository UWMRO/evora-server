#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# @Author: José Sánchez-Gallego (gallegoj@uw.edu)
# @Date: 2022-11-30
# @Filename: server.py
# @License: BSD 3-clause (http://www.opensource.org/licenses/BSD-3-Clause)


import asyncio


async def server_handler(reader, writer):

    while True:
        data_bytes = await reader.readline()
        data_str = data_bytes.decode().strip()

        if data_str == "":
            continue

        if data_str == "hi":
            writer.write(b"Greetings to you!\n")
        elif data_str == "bye":
            writer.write(b"Farewell\n")
        else:
            writer.write(b"I did not get that\n")

        writer.drain()


async def main():
    server = await asyncio.start_server(server_handler, host="0.0.0", port=4000)

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    print(f"Serving on {addrs}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
