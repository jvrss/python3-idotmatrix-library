import asyncio
import random
from idotmatrix import ConnectionManager, Gif


async def main():
    await connection()

    gif = Gif()
    gifs = [
        "./images/demo.gif",
    ]

    while True:
        chosen = random.choice(gifs)
        print(f"exibindo: {chosen}")
        await gif.uploadProcessed(file_path=chosen, pixel_size=32)
        await asyncio.sleep(5)


async def connection():
    conn = ConnectionManager()
    await conn.connectBySearch()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        quit()
