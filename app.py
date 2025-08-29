from flask import Flask
from flask_session import Session
from extensions import init_limiter
from db import init_app
from routes.auth import auth_bp
from routes.stocks import stocks_bp

app = Flask(__name__)
init_app(app)
init_limiter(app)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = "secret_key"
Session(app)

app.register_blueprint(auth_bp)
app.register_blueprint(stocks_bp)


@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


if __name__ == "__main__":
    app.run(debug=True)
