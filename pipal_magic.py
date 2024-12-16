"""pipalhub_magic

Jupyter Lab magic commands for trainings by Pipal Academy.
"""

import argparse
from IPython import get_ipython
from IPython.display import display
from IPython.core.magic import Magics, magics_class, line_magic, cell_magic, needs_local_scope
import sqlite3
from manage import API
import sys
import traceback
from pathlib import Path

api = API.load()

class Problem:
    def __init__(self, name):
        self.name = name
        self.metadata = api.get_problem(name)
        self.logger = _Logger()
        self.checks = [Check.load(c, logger=self.logger) for c in self.metadata['checks']]

    def verify(self, env):
        self._verify(env)

    def _verify(self, env):
        func_name = self.metadata.get("function_name")
        script_name = self.metadata.get("script_name")

        if func_name is None and script_name is None:
            self.logger.log("Sorry, verification is not supported for this problem.")
            return "NOT SUPPORTED"

        if func_name and func_name not in env:
            self.logger.log(f"ERROR: Unable to find function with name {func_name}.")
            return "notfound"
        if script_name and not Path(script_name).exists():
            self.logger.log(f"ERROR: Unable to find program {script_name}.")
            return "notfound"

        passed = True

        checks = self.checks
        print("Found", len(checks), "checks")
        for check in checks:
            check_passed = check.run(env)
            passed = passed and check_passed

        if passed:
            self.logger.log(f"🎉 Congratulations! You have successfully solved problem {self.name}!!")
            return "pass"
        else:
            self.logger.log(f"💥 Oops! Your solution to problem {self.name} is incorrect or incomplete.")
            return "fail"


class Check:
    def __init__(self, spec, logger=None, problem=None):
        self.spec = spec
        self.logger = logger or _Logger()
        self.problem = problem

    @staticmethod
    def load(spec, logger=None, problem=None):
        if "code" in spec:
            return FunctionCheck(spec, logger=logger, problem=problem)
        elif "command" in spec:
            return CommandCheck(spec, logger=logger, problem=problem)
        else:
            raise ValueError(f"Invalid Check spec: {spec!r}")

    def run(self, env):
        raise NotImplementedError()


class FunctionCheck(Check):
    def __init__(self, spec, logger=None, problem=None):
        super().__init__(self, logger=logger, problem=problem)
        self.setup_code = spec.get("setup_code")
        self.code = spec["code"]
        self.name = spec.get("name") or self.code
        self.expected = spec["expected"]

        # hack to allow multi-line code using mode "exec"
        self._mode = spec.get("mode", "eval")

    def do_eval(self, code, env):
        env = env.copy()
        if self._mode == "eval":
            if self.setup_code:
                exec(self.setup_code, env)
            return eval(self.code, env)
        elif self._mode == "exec":
            exec(self.code, env)

            # hack to specify expected in code
            if "_expected" in env:
                self.expected = env["_expected"]

            return env["result"]
        else:
            raise ValueError(f"Invalid mode: {self._mode}")

    def run(self, env):
        env = dict(env)

        # p = self.problem and self.problem.joinpath("_checks.py")
        # if p.exists():
        #     exec(p.read_text(), env)

        try:
            result = self.do_eval(self.code, env)
        except Exception:
            self.logger.log(f"✗ {self.name}")
            sys.stdout.flush()
            traceback.print_exc()
            sys.stderr.flush()
            return False

        if result == self.expected:
            self.logger.log(f"✓ {self.name}")
            return True
        else:
            self.logger.log(f"✗ {self.name}")
            self.logger.log(f"  expected: {self.expected!r}")
            self.logger.log(f"  found: {result!r}")
            return False

class _Logger:
    """Simple logger to capture the logged output."""

    def __init__(self):
        self.lines = []

    def log(self, line):
        self.lines.append(line)
        print(line)

@magics_class
class PipalMagics(Magics):

    @line_magic
    @needs_local_scope
    def verify_problem(self, line, local_ns=None):
        p = Problem(line)
        p.verify(local_ns)

ipython = get_ipython()
ipython.register_magics(PipalMagics)
print("Loaded magic commands: verify_problem")