#!/usr/bin/env python3

# How to run:
# $ ./vms/convert_all.sh && ./vms/run_all_tests.py -vb
# or:
# $ ./convert_all.sh && ./run_all_tests.py -vb

import json
import os
import subprocess
import sys
import unittest

CACHED_ENV = None


class Environment:
    def __init__(self):
        self.potential_testees = []  # List of paths
        self.potential_drivers = []  # List of paths
        self.test_cases = []  # List of tuples of 2 paths (first the testee, then the driver)
        self.counts_per_dir_path = dict()  # map from dir to number of tests


def load_test_cases(dir_path):
    with open(dir_path + "/tests/testcases.json", "r") as fp:
        data = json.load(fp)
    # Sanity check that all entries are tuples of two strings (and hopefully filenames)
    assert all(len(e) == 2 and isinstance(e[0], str) and isinstance(e[1], str) for e in data)
    return [(f"{dir_path}/{testee}.segment", f"{dir_path}/tests/{driver}.segment") for (testee, driver) in data]


def load_all_data() -> Environment:
    env = Environment()
    for maybe_dir in os.listdir():
        if not os.path.isdir(maybe_dir):
            continue
        test_cases = load_test_cases(maybe_dir)
        env.test_cases.extend(test_cases)
        assert maybe_dir not in env.counts_per_dir_path
        env.counts_per_dir_path[maybe_dir] = len(test_cases)
        raw_testees = os.listdir(maybe_dir)
        raw_drivers = os.listdir(maybe_dir + "/tests")
        testees = [f"{maybe_dir}/{t}" for t in raw_testees if t != "tests" and t.endswith(".segment")]
        drivers = [f"{maybe_dir}/tests/{d}" for d in raw_drivers if d.endswith(".segment")]
        env.potential_testees.extend(testees)
        env.potential_drivers.extend(drivers)
    print(f"Loaded {len(env.test_cases)} testcases, found {len(env.potential_testees)} testees and {len(env.potential_drivers)} drivers.")
    return env


class DetectedFiles(unittest.TestCase):
    def test_are_exactly_covered(self):
        used_testees = {e[0] for e in CACHED_ENV.test_cases}
        used_drivers = {e[1] for e in CACHED_ENV.test_cases}
        with self.subTest(part="testee"):
            self.assertEqual(used_testees, set(CACHED_ENV.potential_testees))
        with self.subTest(part="driver"):
            self.assertEqual(used_drivers, set(CACHED_ENV.potential_drivers))

    def test_counts_are_nonzero(self):
        for dir_path, count in CACHED_ENV.counts_per_dir_path.items():
            with self.subTest(dir_path=dir_path):
                self.assertTrue(count > 0)


class ExecuteTestDrivers(unittest.TestCase):
    def execute_driver(self, *cmd_args):
        # Let the unittest framework deal with capturing/displaying the results.
        completed_process = subprocess.run(
            ["cargo", "run", "--", "--mode=test-driver", *cmd_args],
            check=False,
            capture_output=True,
        )
        if 0 == completed_process.returncode:
            return
        # TODO: Output with "-b" is duplicated, and without "-b" it appears in the wrong place. Ugh.
        print(completed_process.stdout.decode())
        print(completed_process.stderr.decode(), file=sys.stderr)
        self.assertEqual(0, completed_process.returncode)
        raise AssertionError("unreachable")

    def test_can_execute_anything(self):
        self.execute_driver("--help")

    def test_the_listed_test_cases(self):
        for testee, driver in CACHED_ENV.test_cases:
            with self.subTest(driver=driver, testee=testee):
                self.execute_driver(driver, testee)


def change_to_this_files_dir():
    os.chdir(os.path.dirname(__file__))


def run():
    global CACHED_ENV
    change_to_this_files_dir()
    CACHED_ENV = load_all_data()
    unittest.main()


if __name__ == "__main__":
    run()
