import asyncio
from idotmatrix import ConnectionManager

from idotmatrix import Gif

async def main():
    await connection()

    # show GIF
    test = Gif()
    await test.uploadProcessed(
        file_path="./images/demo.gif",
        pixel_size=32,
    )


async def connection():
    conn = ConnectionManager()
    await conn.connectBySearch()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        quit()
