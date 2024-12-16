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
import subprocess

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

class CommandCheck(Check):
    def __init__(self, spec, logger=None, problem=None):
        super().__init__(self, logger=logger, problem=problem)

        self.command = spec["command"]
        self.name = spec.get("name") or self.command
        self.sort_output = spec.get("sort_output", False)
        self.expected_output_print = ""
        self.expected_output = self.process_expected_output(spec.get("expected_output"), self.sort_output)
        self.expected_output_print = self.expected_output
        if self.sort_output:
            self.expected_output = self.sort_output_lines(self.expected_output)

        self.test = spec.get("test")

    def process_expected_output(self, expected_output, sort_output):
        if expected_output is None:
            return None
        if isinstance(expected_output, dict):
            cmd = expected_output["command"]

            cmd = cmd.format(PROBLEM_ROOT=self.problem.root)

            p = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, text=True, check=False)
            return self.ignore_trailing_space(p.stdout.strip("\n"))
        else:
            return expected_output.strip("\n")

    def sort_output_lines(self, output):
        lines = output.splitlines()
        return "\n".join(sorted(lines))

    def ignore_trailing_space(self, text):
        lines = [line.rstrip() for line in text.splitlines()]
        return "\n".join(lines)

    def run(self, env):
        env = env.copy()
        # print(f"$ {self.command}")
        p = subprocess.run(
            self.command, shell=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False
        )
        output = p.stdout.strip("\n")
        output = self.ignore_trailing_space(output)
        output_print = output

        if self.sort_output:
            output = self.sort_output_lines(output)

        if self.expected_output is not None:

            # XXX-Anand: Work-around to deal with YAML when there are leading spaces in the first line
            # The trick is to replace the first space with an _ and the following code replaces that back to a space.
            if self.expected_output.startswith("_"):
                self.expected_output = self.expected_output.replace("_", " ", 1)

            if output == self.expected_output:
                self.logger.log(f"✓ {self.name}")
                return True
            else:
                self.logger.log(f"✗ {self.name}")
                self.logger.log(f"Expected:\n{self.expected_output_print}")
                self.logger.log(f"Found:\n{output_print}")
                return False
        elif self.test:
            self.stdout = output
            return self.run_test()
        else:
            return True

    def run_test(self):
        try:
            env = {"stdout": self.stdout}
            # p = self.problem and self.problem.joinpath("_checks.py")
            # if p.exists():
            #     exec(p.read_text(), env)

            exec(self.test, env)
        except Exception:
            self.logger.log(f"✗ {self.name}")
            sys.stdout.flush()
            traceback.print_exc()
            sys.stderr.flush()
            return False
        else:
            self.logger.log(f"✓ {self.name}")
            return True


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