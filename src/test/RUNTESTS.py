#!/usr/bin/env python3
#
# Copyright 2018, Intel Corporation
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in
#       the documentation and/or other materials provided with the
#       distribution.
#
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived
#       from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

""" Entry point for test framework. """

import os
import importlib.util as importutil

from basetest import get_testcases


def import_testfiles():
    """
    Traverse through "src/test" directory, find all "TESTS.py" files and
    import them as modules. Set imported module name to file directory path.
    """
    cwd = os.path.dirname(os.path.realpath(__file__))
    for root, _, files in os.walk(cwd):
        for name in files:
            if name == 'TESTS.py':
                testfile = os.path.join(root, name)
                spec = importutil.spec_from_file_location(
                    os.path.dirname(testfile), testfile)
                module = importutil.module_from_spec(spec)
                spec.loader.exec_module(module)


def run_tests():
    """Run tests imported from repository tree from selected groups"""
    for test in get_testcases():
        t = test()
        if not t.config.group or test.group in t.config.group:
            t.execute()


if __name__ == "__main__":
    import_testfiles()
    run_tests()
