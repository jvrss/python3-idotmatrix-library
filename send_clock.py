import asyncio

from idotmatrix import Clock
from idotmatrix import ConnectionManager

from idotmatrix import Gif

async def main():
    await connection()

    # clock
    test = Clock()
    await test.setMode(4)


async def connection():
    conn = ConnectionManager()
    await conn.connectBySearch()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        quit()
