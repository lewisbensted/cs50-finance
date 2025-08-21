from flask import Blueprint, render_template, request, redirect, session, flash, jsonify
from werkzeug.security import check_password_hash, generate_password_hash
import sqlite3

from db import get_db

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        db = get_db()
        cursor = db.cursor()
        username = request.form.get("username", "").strip()
        password = request.form.get("password")
        if not username:
            return jsonify({"error": "Username not provided"}), 400

        if not password:
            return jsonify({"error": "Password not provided"}), 400

        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user is None or not check_password_hash(user["hash"], password):
            return jsonify({"error": "Invalid username or password"}), 401

        session["user_id"] = user["id"]

        return redirect("/")
    else:
        if session.get("user_id"):
            return redirect("/")

        return render_template("login.html")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        if session.get("user_id"):
            return redirect("/")
        return render_template("register.html")
    else:
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        try:
            db = get_db()
            cursor = db.cursor()
            if not username:
                return jsonify({"error": "Username not provided"}), 400

            if not password or not confirmation:
                return jsonify({"error": "Password(s) not provided"}), 400

            if password != confirmation:
                return jsonify({"error": "Passwords do not match"}), 400

            password_hash = generate_password_hash(password)

            cursor.execute(
                "INSERT INTO users (username, hash) VALUES (?, ?)",
                (username, password_hash),
            )
            db.commit()

            flash("Registration successful", "success")
            return redirect("/login")

        except sqlite3.IntegrityError:
            return jsonify({"error": "Username already exists"}), 409
        except Exception as e:
            print(e)
            return jsonify({"error": "Unexpected error"}), 500
