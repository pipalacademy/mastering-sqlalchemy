"""Script to manage updates and assignment submissions.
"""

import click
import requests
from pathlib import Path
import json
import sys
import os

class API:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.session.auth = (username, password)
        self.base_url = os.getenv("MASTERING_SQLALCHEMY_BASE_URL", "https://mastering-sqlalchemy.apps.pipal.in")

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

        if path.suffix not in (".ipynb", ".py"):
            print("You can only submit .ipynb or .py files", file=sys.stderr)
            sys.exit(2)

        url = "/submit/" + filename
        payload = path.read_bytes()
        r = self.post(url, payload)

        r.raise_for_status()
        print(f"The file {filename} has been submitted successfully!")

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

    def update(self, force=False):
        updates = self.get("/updates").json()['updates']
        current_version = self.read_version() if not force else 0
        for entry in updates:
            version = entry['version']
            if version > current_version:
                print("updating to version", entry['version'])
                self.update_files(entry['files'])
        self.update_version(version)

    def read_version(self):
        try:
            return int(open(".pipal/version.txt").read())
        except IOError:
            return 0

    def update_version(self, version):
        path = Path(".pipal/version.txt")
        path.parent.mkdir(exist_ok=True)
        path.write_text(str(version))

    def update_files(self, files):
        for f in files:
            self.update_file(f)

    def update_file(self, f):
        path = Path(f)
        if path.exists() and path.suffix == ".ipynb":
            print("already exists:", path)
        else:
            data = self.fetch(f)
            path.parent.mkdir(exist_ok=True, parents=True)
            path.write_bytes(data)
            print("saved", path)

    def fetch(self, path):
        url = f"https://raw.githubusercontent.com/pipalacademy/mastering-sqlalchemy/refs/heads/main/{path}"
        return requests.get(url).content

    def get_problem(self, name):
        r = self.get(f"/problems/{name}")
        if r.status_code == 404:
            raise Exception(f"Unknown problem: {name}")
        return r.json()

@click.group()
def app():
    pass

@app.command()
@click.option('--force', is_flag=True, help="force update all versions")
def update(force):
    """Fetch new updates to the repository.
    """
    api = API.load()
    api.update(force=force)

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