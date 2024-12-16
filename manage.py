"""Script to manage updates and assignment submissions.
"""

import click
import requests
from pathlib import Path
import json
import sys

class API:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.base_url = "https://mastering-sqlalchemy.apps.pipal.in"

    def get(self, path):
        url = self.base_url + path
        return self.session.get(url)

    def whoami(self):
        r = self.get("/whoami")
        if r.status_code == 403:
            print("ERROR: Invalid credentials", file=sys.stderr)
            sys.exit(2)
        r.raise_for_status()
        d = r.json()
        print(f"Hello, {d['name']}!")

    @staticmethod
    def load():
        path = Path(".pipal") / "login.json"
        path.parent.mkdir(exist_ok=True)

        if not path.exists():
            print("Please login using `python manage.py login` before running this command.", file=sys.stderr)
            sys.exit(1)

        d = json.loads(path.read_text())
        return API(d['username'], d['password'])

    def save_login(self):
        path = Path(".pipal") / "login.json"
        path.parent.mkdir(exist_ok=True)
        d = {"username": self.username, "password": self.password}
        path.write_text(json.dumps(d))


@click.group()
def app():
    pass

@app.command()
def update():
    """Fetch new updates to the repository.
    """
    print("Not yet implemented!")

@app.command()
def submit():
    """Submits an assignment
    """
    print("Not yet implemented!")

@app.command()
def whoami():
    api = API.load()
    api.whoami()

@app.command()
@click.option("--email", prompt=True, help="Your email address")
@click.option("--password", prompt=True, hide_input=True, help="Your password")
def login(email, password):
    """Logs in a user
    """
    api = API(email, password)
    print()
    api.whoami()
    api.save_login()
    print("Login successful!")


if __name__ == "__main__":
    app()