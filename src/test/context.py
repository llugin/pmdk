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
"""Set of classes that represent the context of single test execution
(like build, filesystem, duration)"""

import os
import sys
from datetime import datetime
import subprocess as sp
from collections import Iterable

from helpers import Colors, Message

class Context:
    """ This class sets the context of the variables. """

    def __init__(self, test, conf, fs, build):
        self.proc, self.start_time, self.end_time = None, None, None
        self.test = test
        self.conf = conf
        self.build = build
        self.fs = fs
        self.testdir = os.path.join(fs.dir, test.testdir)

    def create_holey_file(self, size, name):
        """ Ccreate a new file with the selected size and name. """
        filepath = os.path.join(self.testdir, name)
        with open(filepath, 'w') as f:
            f.seek(size)
            f.write('\0')
        return filepath

    def test_exec(self, cmd, args=''):
        """ This method runs the given command depending on the system. """
        if sys.platform == "win32":
            cmd = os.path.join(self.build.exedir, cmd) + '.exe'
        else:
            cmd = os.path.join(self.test.cwd, cmd) + self.build.exesuffix

        self.start_time = datetime.now()
        env = {**self.build.env, **self.test.utenv}
        try:
            self.proc = sp.run([cmd, args],
                               timeout=self.conf.test_timeout.total_seconds(),
                               env=env, stdout=sp.PIPE, cwd=self.test.cwd,
                               stderr=sp.STDOUT, universal_newlines=True)
        except sp.TimeoutExpired:
            self.test.timeout = True
            Message(self.conf).print('Skipping: {} {} timed out{}'.format(
                self.test.name, Colors.RED, Colors.END))

        finally:
            self.end_time = datetime.now()


def init_ctx_classes(conf, args):
    """ Helper function for initializing context classes that can return list
    of objects during initializiaton"""
    def expand():
        flattened = []
        for arg in args:
            if isinstance(arg(conf), Iterable):
                for a in arg(conf):
                    flattened.append(a)
            else:
                flattened.append(arg)
        return flattened

    return [cls(conf) for cls in expand()]


class Build:
    """ This class returns a list of build types based on arguments.
        If class is empty, treats like "all"."""

    def __str__(self):
        return self.__class__.__name__.lower()

    @classmethod
    def factory(cls, conf, *args):
        return init_ctx_classes(conf, args)


class Debug(Build):
    """ This class sets the context for debug build"""

    def __init__(self, conf):
        self.env = os.environ.copy()
        self.exesuffix = ''
        if sys.platform == 'win32':
            builddir = os.path.abspath(os.path.join(
                conf.rootdir, '..', 'x64', 'Debug'))
            self.exedir = os.path.join(builddir, 'tests')
            self.env['PATH'] = self.env['PATH'] + \
                os.pathsep + os.path.join(builddir, 'libs')
        else:
            self.env['LD_LIBRARY_PATH'] = os.path.join(
                conf.rootdir, '..', 'debug')


class Nondebug(Build):
    """ This class sets the context for nondebug build"""

    def __init__(self, conf):
        self.env = os.environ.copy()
        self.exesuffix = ''

        if sys.platform == 'win32':
            builddir = os.path.abspath(os.path.join(
                conf.rootdir, '..', 'x64', 'Release'))
            self.exedir = os.path.join(builddir, 'tests')
            self.env['PATH'] = self.env['PATH'] + os.pathsep + os.path.join(
                builddir, 'libs')
        else:
            self.env['LD_LIBRARY_PATH'] = os.path.join(
                conf.rootdir, '..', 'nondebug')


# Build types not available on Windows
if sys.platform != 'win32':
    class Static_Debug(Build):
        """ Sets the context for static_debug build"""

        def __init__(self, conf):
            self.env = os.environ.copy()
            self.exesuffix = '.static-debug'
            self.env['LD_LIBRARY_PATH'] = os.path.join(
                conf.rootdir, '..', 'debug')

    class Static_Nondebug(Build):
        """ Sets the context for static_nondebug build"""

        def __init__(self, conf):
            self.env = os.environ.copy()
            self.exesuffix = '.static-nondebug'
            self.env['LD_LIBRARY_PATH'] = os.path.join(
                conf.rootdir, '..', 'nondebug')


class Fs:
    """ This class returns a list of filesystem types based on arguments.
        If class is empty, treats like "all". """

    def __repr__(self):
        return self.__class__.__name__.lower()

    @classmethod
    def factory(cls, conf, *args):
        return init_ctx_classes(conf, args)


class Pmem(Fs):
    """ This class sets the context for pmem filesystem"""

    def __init__(self, conf):
        self.dir = os.path.abspath(conf.pmem_fs_dir)


class Nonpmem(Fs):
    """ This class sets the context for nonpmem filesystem"""

    def __init__(self, conf):
        self.dir = conf.non_pmem_fs_dir


class NoFs(Fs):
    def __init__(self, conf):
        pass


class AllFs(Fs):
    def __new__(cls, *args):
        return (Pmem, Nonpmem)

    def __init__(self, conf):
        pass


class AnyFs(Fs):
    def __init__(self, conf):
        pass


class Duration:
    """ Base class for test duration. """

    def __repr__(self):
        return self.__class__.__name__.lower()

    def __iter__(self):
        if not hasattr(self, 'including'):
            self.including = [self.__class__]
        for i in self.including:
            yield i


class Short(Duration):
    pass


class Medium(Duration):
    pass


class Long(Duration):
    pass


class Check(Duration):
    def __init__(self):
        self.including = [Short, Medium, Check]


class AllTypes(Duration):
    def __init__(self):
        self.including = [Short, Medium, Check, Long]
