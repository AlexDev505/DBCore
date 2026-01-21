import asyncio
import os
import sys

sys.path.append("..")
from models import User

from aiodbcore import Database

DB_FILE_PATH = "db.sqlite"
DB_PATH = f"sqlite://{DB_FILE_PATH}"


class DB(Database[User]):
    def create_tables(self):
        with self as db:
            db.create_tables()

    def my_query(self):
        with self as db:
            return db.fetchone(User)

    async def my_async_query(self):
        async with self as db:
            return await db.fetchone(User)


async def main():
    DB.init(DB_PATH)
    db = DB()

    db.create_tables()

    with db as sync_db:  # sync_db has type `SyncDBCore[User]`
        sync_db.insert(User(name="John", age=30))

    async with db as async_db:  # async_db has type `AsyncDBCore[User]`
        print(await async_db.fetchall(User))


if __name__ == "__main__":
    asyncio.run(main())

    DB.close_connections()  # it can be called from asyncio event loop.
    os.remove(DB_FILE_PATH)
