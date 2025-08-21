# CS50 Finance

A web app using real-time data from the IEX Stock Exchange to allow users to buy and sell shares in companies.

## Setup

1. Clone this repo:

```sh
  git clone https://github.com/lewisbensted/cs50-finance.git
```
2. In the project [root directory](/), create and activate your own virtual environment:
```sh
  cd cs50-finance
  python -m venv .venv

  source .venv/bin/activate   # Linux/macOS
  .venv\Scripts\Activate      # Windows
```
3. Install dependencies:

```sh
  pip install -r requirements.txt
```

4. Initialise database:
```sh
    export FLASK_APP=app.py     # Linux/macOS
    set FLASK_APP=app.py        # Windows

    flask init-db
```

## Tech Stack

[![My Skills](https://skillicons.dev/icons?i=js,css,html,flask,py,sqlite)](https://skillicons.dev)
