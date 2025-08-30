from flask import (
    Blueprint,
    current_app,
    render_template,
    request,
    redirect,
    session,
    jsonify,
)
from extensions import limiter
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3
import re

from db import get_db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def login():
    if request.method == "POST":
        db = get_db()
        cursor = db.cursor()
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "Missing request body"}), 400

            username = data.get("username", "").strip()
            password = data.get("password", "")

            if not username:
                return jsonify({"error": "Username not provided"}), 400

            if not password:
                return jsonify({"error": "Password not provided"}), 400

            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

            if user is None or not check_password_hash(user["hash"], password):
                return jsonify({"error": "Invalid username or password"}), 401

            session["user_id"] = user["id"]

            return jsonify({"success": True, "message": "Login successful"}), 200
        except Exception as e:
            current_app.logger.exception(e)
            return jsonify({"error": "Unexpected error"}), 500
    else:
        if session.get("user_id"):
            return redirect("/")

        return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/")


@auth_bp.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per hour", methods=["POST"])
def register():
    if request.method == "GET":
        if session.get("user_id"):
            return redirect("/")
        return render_template("register.html")
    else:
        db = get_db()
        cursor = db.cursor()

        passwordExp1 = (
            r"(?=.*?[a-zA-Z])(?=.*?[0-9])(?=.*?[$&+,:;=?@#|'<>.^*.()%!-/\\]).+$"
        )
        passwordExp2 = r"\S*$"

        try:
            data = request.get_json()

            if not data:
                return jsonify({"error": "Missing request body"}), 400

            username = data.get("username", "").strip()
            password = data.get("password", "")
            confirmation = data.get("confirmation", "")

            if not username:
                return jsonify({"error": "Username not provided"}), 400

            if not len(username) >= 3:
                return jsonify({"error": "Username not long enough"}), 400

            if not password or not confirmation:
                return jsonify({"error": "Password(s) not provided"}), 400

            if not re.fullmatch(passwordExp1, password):
                return (
                    jsonify(
                        {
                            "error": "Password must contain a number, letter and special character"
                        }
                    ),
                    400,
                )

            if not re.fullmatch(passwordExp2, password):
                return jsonify({"error": "Password cannot contain spaces"}), 400

            if password != confirmation:
                return jsonify({"error": "Passwords do not match"}), 400

            password_hash = generate_password_hash(password)

            cursor.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                (username, password_hash),
            )
            db.commit()

            return jsonify({"success": True, "message": "Registration successful"}), 201

        except sqlite3.IntegrityError:
            return jsonify({"error": "Username already exists"}), 409
        except Exception as e:
            current_app.logger.exception(e)
            return jsonify({"error": "Unexpected error"}), 500
