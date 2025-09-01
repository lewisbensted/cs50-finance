import requests

from flask import redirect, session
from functools import wraps


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)

    return decorated_function


def lookup(symbol):
    """Look up quote for symbol."""
    url = f"https://finance.cs50.io/quote?symbol={symbol.upper()}"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an error for HTTP error responses
        quote_data = response.json()
        return {
            "name": quote_data["companyName"],
            "price": quote_data["latestPrice"],
            "symbol": symbol.upper(),
        }
    except requests.RequestException as e:
        print(f"Request error: {e}")
    except (KeyError, ValueError) as e:
        print(f"Data parsing error: {e}")
    return None


def validate_transaction(data):
    valid = []
    invalid = []

    for symbol, shares in data.items():
        symbol = symbol.strip()
        if not isinstance(symbol, str) or not symbol:
            invalid.append(
                {"symbol": symbol, "shares": shares, "error": "Invalid symbol"}
            )
            continue
        try:
            if isinstance(shares, bool):
                raise ValueError
            shares = float(shares)
            if not shares.is_integer() or shares < 1:
                raise ValueError

            valid.append({"symbol": symbol, "shares": int(shares)})
        except (TypeError, ValueError):
            invalid.append(
                {
                    "symbol": symbol,
                    "shares": shares,
                    "error": "Shares must be a positive integer",
                }
            )
            continue

    return valid, invalid
