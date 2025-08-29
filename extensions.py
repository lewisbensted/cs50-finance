from flask_limiter import Limiter
from flask import jsonify, request, session


def user_or_ip():
    if session.get("user_id"):
        return f"user:{session['user_id']}"
    return f"ip:{request.remote_addr}"

limiter = Limiter(
    key_func=user_or_ip
)

def init_limiter(app):
    limiter.init_app(app)
    
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return jsonify({
            "error": "Too many requests"
        }), 429