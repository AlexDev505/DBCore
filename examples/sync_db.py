"""

SyncDBCore has the same interface as the async version.
You just need to remove all the `await` statements and use `SyncDBCore`.

"""

import sys

sys.path.append("..")
from models import User

from aiodbcore import SyncDBCore

DB_PATH = "sqlite+sqlite3://:memory:"


class DB(SyncDBCore[User]):
    def get_old_peoples(self) -> list[User]:
        return self.fetchall(User, where=User.age >= 20)


def main():
    DB.init(DB_PATH)
    db = DB()
    db.create_tables()  # Creates all tables

    # insert some data in db
    stas, alex = db.insert(
        [User(name="Stas", age=21), User(name="Alex", age=20)]
    )

    # fetching data
    old_peoples = db.get_old_peoples()
    print("old peoples:", *old_peoples, sep="\n")

    # updating data
    db.update(
        User,
        {User.moneys: User.moneys + 1500},
        where=User.age.contained((20, 21)),
    )  # where User.age IN (20, 21)
    print("new moneys:", *(db.fetchall(User)), sep="\n")

    # dropping tables
    db.drop_table(User)

    DB.close_connections()


if __name__ == "__main__":
    main()
