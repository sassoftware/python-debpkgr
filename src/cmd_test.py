#!/usr/bin/env python

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import subprocess
import select
import os
import tempfile
import shutil

from six import text_type

try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    from unittest import mock  # noqa
except ImportError:
    import mock  # noqa

class RunCmdError(Exception):
    '''Raised when a command fails'''


def cmd_readout(cmd, cwd=None, chunk=16):
    '''
    cmd : list of command line ops
    chunk : bytes to read
    '''
    stdout = b''
    stderr = b''
    PIPE = subprocess.PIPE
    p = subprocess.Popen(cmd, shell=False, stdin=None,
                         cwd=cwd, stdout=PIPE, stderr=PIPE)
    readers = [p.stdout, p.stderr]
    while True:
        reader, _, _ = select.select(readers, [], readers, 15)
        if p.stdout in reader:
            data = os.read(p.stdout.fileno(), chunk)
            stdout += data
            if data == b'':
                readers.remove(p.stdout)
        if p.stderr in reader:
            data = os.read(p.stderr.fileno(), chunk)
            stderr += data
            if data == b'':
                readers.remove(p.stderr)
        if p.poll() is not None:
            if (not readers or not reader):
                break
            elif not readers:
                p.wait()

    retval = p.returncode
    stdout = stdout.decode("utf-8", "replace")
    stderr = stderr.decode("utf-8", "replace")
    if retval != 0:
        raise RunCmdError(stdout, stderr)
    return {'retval': retval, 'stdout': stdout, 'stderr': stderr}


class TestCase(unittest.TestCase):
    test_dir = 'cmd_readout_test-'
    def setUp(self):
        test_dir = tempfile.mkdtemp(prefix=self.test_dir)
        self.workspace = os.path.join(test_dir, "workspace")
        old_dir = os.getcwd()
        os.chdir(self.work_dir)
        print(os.getcwd())
        self.addCleanup(shutil.rmtree, self.work_dir, ignore_errors=True)
        self.addCleanup(os.chdir, old_dir)

    def mkfile(self, path, contents=None):
        if contents is None:
            contents = "\n"
        fpath = os.path.join(self.test_dir, path)
        if isinstance(contents, text_type):
            mode = 'w'
        else:
            mode = 'wb'
        with open(fpath, mode) as fh:
            fh.write(contents)
        return fpath

    def mkdir(self, path):
        path = os.path.join(self.test_dir, path)
        os.makedirs(path)
        return path

    @mock.patch('subprocess.Popen')
    def test_cmd_readout_pass(_mock_popen):
        cmd = ['ls']
        out = [ 'a.txt' , 'b.txt', 'c.txt' ]
        _mock_popen.return_value.communicate.return_value = (b"out", b"err")
        _mock_popen.return_value.returncode = 1


    @mock.patch('subprocess.Popen')
    def test_cmd_readout_fail(_mock_popen):
        cmd = ['ls', 'al']
        _mock_popen.return_value.communicate.return_value = (b"out", b"err")
        _mock_popen.return_value.returncode = 1


