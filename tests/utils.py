


"""Utilities used by more than one test."""


import json
import os


__TESTDATADIR = "../tests"


def load_test_data(fname):
    return json.loads(open(os.path.join(__TESTDATADIR, fname)).read())
