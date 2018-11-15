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

"""Base tests class and its functionalities"""

import builtins
import shutil
import subprocess
import sys
from os import path, makedirs, listdir

import context as ctx
from configurator import Configurator
from helpers import Colors, Message

sys.path.insert(0, '..')

if not hasattr(builtins, 'testcases'):
    builtins.testcases = []


def get_testcases():
    return builtins.testcases


def testcase_main():
    """Default main function for running single test group
    using group/TESTS.py as entry point"""
    for test in BaseTest.__subclasses__():
        test().execute()


class Register(type):
    """Metaclass for BaseTest that is used for registering imported tests """

    def __init__(cls, name, bases, dct):
        new = type.__init__(cls, name, bases, dct)
        if cls.__base__.__name__ == 'BaseTest':
            builtins.testcases.append(cls)


class BaseTest(metaclass=Register):
    """Every test case need to inherit from this class"""
    config = Configurator().parse_config()
    _config_builds = ctx.Build.factory(config, *config.build_type)
    _config_fs = ctx.Fs.factory(config, *config.fs_type)
    fs, builds = None, None
    duration = ctx.Check
    match = True
    msg = Message(config)

    def __repr__(self):
        return '{}/{}'.format(self.group, self.__class__.__name__)

    def __init__(self):
        if self.__module__ == '__main__':
            self.cwd = path.dirname(path.abspath(sys.argv[0]))
        else:
            self.cwd = self.__module__

        self.failed, self.timeout = False, False
        self.group = path.basename(self.cwd)
        self.name = self.__class__.__name__

        try:
            self.testnum = int(self.name.replace('TEST', ''))
        except ValueError as e:
            print(
                'Invalid test class name {}, should be "TEST[number]"'.format(self.name))
            raise e

        self.testdir = self.group + '_' + str(self.testnum)
        self.set_contextes()
        self.utenv = self.get_utenv()

    def set_contextes(self):
        """ Initialize contexts list meant to be run based on config settings """
        self.builds = ctx.Build.factory(
            self.config, *self.builds) if self.builds else self._config_builds
        self.builds = [b for b in self.builds if type(b) in [type(cb) for cb in
                                                             self._config_builds]]
        self.fs = ctx.Fs.factory(
            self.config, *self.fs) if self.fs else self._config_fs
        self.fs = [f for f in self.fs if type(f) in [type(cf) for cf in
                                                     self._config_fs]]
        self.ctxs = []
        for fs in self.fs:
            for build in self.builds:
                self.ctxs.append(ctx.Context(self, self.config, fs, build))

    def get_utenv(self):
        """Get environment variables values used by C test framework"""
        return {
            'UNITTEST_NAME': str(self),
            'UNITTEST_LOG_LEVEL': str(self.config.unittest_log_level),
            'UNITTEST_NUM': str(self.testnum)
        }

    def execute(self):
        """Execute test for each context"""
        if all([self.duration not in conf_type()
                for conf_type in self.config.test_type]):
            # do not run
            return

        for ctx in self.ctxs:
            self.failed, self.timeout = False, False
            print('{}: SETUP ({}/{}/{})'.format(self,
                                                self.duration(), ctx.fs, ctx.build))
            self.setup(ctx)
            self.run(ctx)
            self.check(ctx)
            self.clean(ctx.testdir)
            if self.failed and not self.config.keep_going:
                sys.exit(1)

    def setup(self, ctx):
        """ Test setup """
        if not path.exists(ctx.testdir):
            makedirs(ctx.testdir)

    def run(self, ctx):
        """ Implements main test body, run with specific context provided through
        Context class instance. Needs to be implemented by each test """
        raise NotImplementedError('{} does not implement run() method'.format(
            self.__class__))

    def check(self, ctx):
        """ Determine test result """
        if ctx.proc.returncode != 0:
            return self.fail(ctx.proc.stdout)

        if self.match:
            match_proc = self.run_match()
            if match_proc.returncode != 0:
                return self.fail(match_proc.stdout)

        return self.test_passed(ctx)

    def fail(self, text=''):
        """ Prints fail message. """
        self.failed = True
        if text:
            print(text)
        self.msg.print('{}FAILED {}'.format(Colors.RED, Colors.END))

    def run_match(self):
        """ Matches log files. """
        prefix = 'perl ' if sys.platform == 'win32' else ''

        cwd_files = [path.join(self.cwd, f) for f in listdir(self.cwd
                                                             ) if path.isfile(path.join(self.cwd, f))]

        postfix = '{}.log.match'.format(self.testnum)

        # match file ends with match postfix, char before postfix is not a
        # digit
        match_files = [mf for mf in cwd_files if mf.endswith(postfix) and
                       not mf[-len(postfix) - 1].isdigit()]

        match_cmd = prefix + path.join(self.config.rootdir, 'match')
        for mf in match_files:
            cmd = '{} {}'.format(match_cmd, mf)
            return subprocess.run(cmd.split(), stdout=subprocess.PIPE, cwd=self.cwd,
                                  stderr=subprocess.STDOUT, universal_newlines=True)

    def clean(self, testdir):
        """ Removes directory, even if it is not empty. """
        shutil.rmtree(testdir, ignore_errors=True)

    def test_passed(self, ctx):
        """ Print message specific for passed test """
        elapsed = ctx.end_time - ctx.start_time
        if elapsed.total_seconds() < 61:
            sec_test = float(elapsed.total_seconds())
            elapsed = "%06.3f" % sec_test

        tm = '\t\t\t[{}] s'.format(elapsed) if self.config.tm else ''

        self.msg.print(
            '{}: {}PASS {} {}'.format(self, Colors.GREEN, Colors.END, tm))
