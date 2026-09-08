import argparse
import asyncio
import json

import websockets


async def probe(uri: str) -> None:
    async with websockets.connect(uri) as socket:
        message = json.loads(await asyncio.wait_for(socket.recv(), timeout=5))
        print(json.dumps(message, separators=(",", ":")))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("uri", nargs="?", default="ws://127.0.0.1:8081/ws")
    asyncio.run(probe(parser.parse_args().uri))
