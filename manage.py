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

    def post(self, path, data, **kwargs):
        url = self.base_url + path
        return self.session.post(url, data=data, **kwargs)

    def whoami(self):
        r = self.get("/whoami")
        if r.status_code == 403:
            print("ERROR: Invalid credentials", file=sys.stderr)
            sys.exit(2)
        r.raise_for_status()
        d = r.json()
        print(f"Hello, {d['name']}!")

    def submit(self, filename):
        path = Path(filename)
        assignment = path.stem

        url = "/assignments/" + assignment
        payload = path.read_text()
        r = self.post(url, payload)

        r.raise_for_status()
        print(f"Assignment {assignment} is submitted successfully!")

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

    def update(self):
        updates = self.get("/updates").json()['updates']
        for entry in updates:
            print("updating to version", entry['version'])
            self.update_files(entry['files'])

    def update_files(self, files):
        for f in files:
            self.update_file(f)

    def update_file(self, f):
        path = Path(f)
        if path.exists() and path.suffix == ".ipynb":
            print("already exists:", path)
        else:
            text = self.fetch(f)
            path.parent.mkdir(exist_ok=True, parents=True)
            path.write_text(text)
            print("saved", path)

@click.group()
def app():
    pass

@app.command()
def update():
    """Fetch new updates to the repository.
    """
    api = API.load()
    api.update()

@app.command()
@click.argument('filename')
def submit(filename):
    """Submits an assignment
    """
    api = API.load()
    api.submit(filename)

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