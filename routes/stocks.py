from flask import (
    Blueprint,
    render_template,
    request,
    session,
    jsonify,
    current_app,
)
from errors import BadRequestError, NotFoundError
from db import fetch_holdings, get_db
from helpers import login_required, lookup, validate_transaction
from extensions import limiter

stocks_bp = Blueprint("stocks", __name__)


@stocks_bp.route("/prices")
@limiter.limit("60 per minute")
@login_required
def fetch_prices():
    symbols_str = request.args.get("symbols")
    if not symbols_str:
        return jsonify({"error": "No symbols provided"}), 400
    updated_prices = []
    symbols = symbols_str.split(",")

    for symbol in symbols:
        info = lookup(symbol)
        if info:
            updated_prices.append(info)
    if len(symbols) == 1 and len(updated_prices) == 0:
        return ({"error": "Symbol not found"}), 404
    return jsonify(updated_prices), 200


@stocks_bp.route("/")
@login_required
def index():
    try:
        holdings = fetch_holdings(session["user_id"])
    except Exception as error:
        current_app.logger.error(error)
        holdings = None
    return render_template("index.html", holdings=holdings)


@stocks_bp.route("/holdings")
@login_required
def holdings():
    symbol = request.args.get("symbol")
    try:
        holding = fetch_holdings(session["user_id"], symbol)
        return jsonify(holding), 200
    except Exception as error:
        current_app.logger.error(error)
        return jsonify({"error": "Unexpected error"}), 500


@stocks_bp.route("/balance")
@login_required
def fetch_balance():
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT cash FROM users WHERE id = ?", (session["user_id"],))
    row = cursor.fetchone()
    if not row:
        return ({"error": "User not found"}), 404
    return jsonify({"balance": row["cash"]})


@stocks_bp.route("/transactions")
@login_required
def transactions():
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "SELECT "
            "company_name, symbol, price, shares, transaction_type, "
            "timestamp, transaction_type, ROUND(shares * price, 2) "
            "AS value FROM transactions "
            "WHERE user_id = ? ORDER BY timestamp DESC;",
            (session["user_id"],),
        )
        transactions = cursor.fetchall()
        return render_template("transactions.html", transactions=transactions)
    except Exception as e:
        current_app.logger.exception(e)
        return ({"error": "Unexpected error"}), 500


@stocks_bp.route("/search")
@login_required
def search():
    return render_template("search.html")


@stocks_bp.route("/buy", methods=["POST"])
@limiter.limit("30 per minute")
@login_required
def buy():
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Missing or invalid request body"}), 400

    valid, invalid = validate_transaction(data)

    successful = []
    failed = []

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT cash FROM users WHERE id = ?", (session["user_id"],))
        row_cash = cursor.fetchone()
        if not row_cash:
            raise NotFoundError("User not found")
        cash = row_cash["cash"]

        transaction_cache = {}
        total = 0

        for purchase in valid:
            symbol = purchase["symbol"].upper()
            shares = purchase["shares"]

            info = lookup(symbol)
            if not info:
                purchase["error"] = "Symbol not found"
                failed.append(purchase)
                continue
            transaction_cache[symbol] = {
                "price": info["price"],
                "name": info["name"],
                "shares": shares,
                "transaction": purchase,
            }

            price = transaction_cache[symbol]["price"]
            total += price * shares

        if total > cash:
            raise BadRequestError("Insufficient funds")

        for symbol, info in transaction_cache.items():
            shares = info["shares"]
            price = info["price"]
            company_name = info["name"]

            cursor.execute(
                "INSERT INTO transactions "
                "(user_id, symbol, company_name,shares, price, transaction_type) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session["user_id"],
                    symbol,
                    company_name,
                    shares,
                    price,
                    "buy",
                ),
            )
            cursor.execute(
                "INSERT INTO holdings (user_id, symbol, shares, company_name) "
                "VALUES (?, ?, ?, ?) "
                "ON CONFLICT(user_id, symbol) DO UPDATE "
                "SET shares = shares + excluded.shares;",
                (session["user_id"], symbol, shares, company_name),
            )
            successful.append(info["transaction"])
        cash -= total
        cursor.execute(
            "UPDATE users SET cash = ? WHERE id = ?",
            (cash, session["user_id"]),
        )
        db.commit()
        if len(successful):
            return (
                jsonify(
                    {
                        "updated_balance": cash,
                        "successful": successful,
                        "failed": failed + invalid,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify({"error": "No trades executed", "failed": failed + invalid}),
                422,
            )

    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except BadRequestError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        db.rollback()
        current_app.logger.exception(e)
        return jsonify({"error": "Unexpected error"}), 500


@stocks_bp.route("/sell", methods=["POST"])
@limiter.limit("30 per minute")
@login_required
def sell():
    data = request.get_json()
    if not data or not isinstance(data, dict):
        return jsonify({"error": "Missing or invalid request body"}), 400

    valid, invalid = validate_transaction(data)

    successful = []
    failed = []

    transaction_cache = {}

    db = get_db()
    cursor = db.cursor()

    try:
        cursor.execute("SELECT cash FROM users WHERE id = ?", (session["user_id"],))
        row_cash = cursor.fetchone()
        if not row_cash:
            raise NotFoundError("User not found")
        cash = row_cash["cash"]

        for sale in valid:
            symbol = sale["symbol"].upper()
            shares = sale["shares"]

            info = lookup(symbol)
            if not info:
                sale["error"] = "Symbol not found"
                failed.append(sale)
                continue
            transaction_cache[symbol] = {
                "price": info["price"],
                "name": info["name"],
                "shares": shares,
                "transaction": sale,
            }

        for symbol, info in transaction_cache.items():
            shares = info["shares"]
            price = info["price"]
            company_name = info["name"]

            cursor.execute(
                "SELECT shares FROM holdings WHERE user_id = ? AND symbol = ?",
                (session["user_id"], symbol),
            )
            row_holding = cursor.fetchone()
            if not row_holding:
                info["transaction"]["error"] = "Holding not found"
                failed.append(info["transaction"])
                continue

            current_shares = row_holding["shares"]
            if shares > current_shares:
                info["transaction"]["error"] = "Insufficient shares"
                failed.append(info["transaction"])
                continue

            cash += price * shares

            cursor.execute(
                "INSERT INTO transactions "
                "(user_id, symbol, shares, price, transaction_type, company_name) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    session["user_id"],
                    symbol,
                    shares,
                    price,
                    "sell",
                    company_name,
                ),
            )
            cursor.execute(
                "UPDATE holdings "
                "SET shares = shares - ? WHERE user_id = ? AND symbol = ?",
                (shares, session["user_id"], symbol),
            )
            cursor.execute(
                "DELETE FROM holdings WHERE shares = 0 AND user_id = ? AND symbol = ?",
                (session["user_id"], symbol),
            )

            successful.append(info["transaction"])
        cursor.execute(
            "UPDATE users SET cash = ? WHERE id = ?",
            (cash, session["user_id"]),
        )
        db.commit()

        if len(successful):
            return (
                jsonify(
                    {
                        "updated_balance": cash,
                        "successful": successful,
                        "failed": failed + invalid,
                    }
                ),
                200,
            )
        else:
            return (
                jsonify({"error": "No trades executed", "failed": failed + invalid}),
                422,
            )

    except NotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        db.rollback()
        current_app.logger.exception(e)
        return jsonify({"error": "Unexpected error"}), 500
