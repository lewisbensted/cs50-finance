import sqlite3
import click
from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect("finance.db")
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(exception):
    db = g.pop("db", None)
    if db is not None:
        db.close()
    if exception:
        current_app.logger.error(f"Exception during request: {exception}")

def init_db():
    db = sqlite3.connect("finance.db")
    cursor = db.cursor()
    cursor.executescript(open("schema.sql").read())
    db.commit()
    db.close()

@click.command("init-db")
def init_db_command():
    init_db()
    click.echo("Database initialized.")

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)


def fetch_holdings(user_id, symbol=None):
    db = get_db()
    cursor = db.cursor()

    if symbol:
        cursor.execute(
            "SELECT symbol, shares FROM holdings WHERE user_id = ? AND symbol = ?",
            (user_id, symbol),
        )
        row = cursor.fetchone()
        return dict(row) if row else {"symbol": symbol, "shares": 0}

    else:
        cursor.execute(
            "SELECT symbol, shares, name FROM holdings WHERE user_id = ? AND shares > 0",
            (user_id,),
        )
        return [dict(row) for row in cursor.fetchall()]
