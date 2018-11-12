#
# Copyright (c) SAS Institute Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os

from debpkgr.signer import SignOptions, SignerError, Signer
from debpkgr.signer import sign_file

from tests import base


class SignerBaseTest(base.BaseTestCase):

    def setUp(self):
        super(SignerBaseTest, self).setUp()
        signme = ('#!/bin/bash -e\n'
                  'echo $0\n'
                  'echo GPG_KEYID=$GPG_KEYID\n'
                  'echo GPG_REPOSITORY_NAME=$GPG_REPOSITORY_NAME\n'
                  'echo GPG_DIST\n'
                  'exit 0\n'
                  )
        self.sign_cmd = self.mkfile("signme", contents=signme)
        os.chmod(self.sign_cmd, 0o755)
        self.key_id = '8675309'
        self.repository_name = 'jenny'
        self.dist = 'tutone'


class SignerTestSign(SignerBaseTest):

    @base.mock.patch("debpkgr.signer.tempfile.NamedTemporaryFile")
    @base.mock.patch("debpkgr.signer.subprocess.Popen")
    def test_sign(self, _Popen, _NamedTemporaryFile):
        filename = self.mkfile("Random_File", contents="Name: Random_File")
        kwargs = dict(dist=self.dist, repository_name=self.repository_name)
        so = SignOptions(cmd=self.sign_cmd, key_id=self.key_id, **kwargs)

        _Popen.return_value.wait.return_value = 0
        signer = Signer(options=so)
        signer.sign(filename)

        _Popen.assert_called_once_with(
            [self.sign_cmd, filename],
            env=dict(
                GPG_CMD=self.sign_cmd,
                GPG_KEY_ID=self.key_id,
                GPG_REPOSITORY_NAME=self.repository_name,
                GPG_DIST=self.dist,
            ),
            stdout=_NamedTemporaryFile.return_value,
            stderr=_NamedTemporaryFile.return_value,
        )

    @base.mock.patch("debpkgr.signer.tempfile.NamedTemporaryFile")
    @base.mock.patch("debpkgr.signer.subprocess.Popen")
    def test_sign_error(self, _Popen, _NamedTemporaryFile):
        filename = self.mkfile("Release", contents="Name: Release")
        so = SignOptions(cmd=self.sign_cmd)

        _Popen.return_value.wait.return_value = 2
        signer = Signer(options=so)
        with self.assertRaises(SignerError) as ctx:
            signer.sign(filename)
        self.assertEqual(
            _NamedTemporaryFile.return_value,
            ctx.exception.stdout)
        self.assertEqual(
            _NamedTemporaryFile.return_value,
            ctx.exception.stderr)

    def test_bad_signing_options(self):
        bad_so = "SoWhat"
        with self.assertRaises(ValueError) as ctx:
            Signer(options=bad_so)
        self.assertTrue(
            str(ctx.exception).startswith('Signer options: unexpected type'))


class SignErrorTest(SignerBaseTest):

    def test_raise_errors(self):
        err = dict(stdout='STDOUT', stderr='STDERR')
        msg = "Signer Error"
        with self.assertRaises(SignerError) as ctx:
            raise SignerError(msg, **err)
        self.assertTrue(msg in str(ctx.exception))
        self.assertEqual(ctx.exception.stdout, err['stdout'])
        self.assertEqual(ctx.exception.stderr, err['stderr'])


class SignOptionsTest(SignerBaseTest):

    def test_cmd_shlex(self):
        sign_cmd = self.sign_cmd + ' -e -n "$GPG_KEY_ID"'
        expected = [self.sign_cmd, '-e', '-n', '"$GPG_KEY_ID"']
        so = SignOptions(cmd=sign_cmd, key_id='8675309')
        self.assertTrue(so._cmdargs, expected)

    def test_bad_cmd(self):
        with self.assertRaises(SignerError) as ctx:
            SignOptions()
        self.assertEqual(
            "Command not specified",
            str(ctx.exception))

        with self.assertRaises(SignerError) as ctx:
            SignOptions(cmd="/tmp")
        self.assertEqual(
            "Command /tmp is not a file",
            str(ctx.exception))

        cmd = self.mkfile("not-executable", contents="whatever")
        with self.assertRaises(SignerError) as ctx:
            SignOptions(cmd=cmd)
        self.assertEqual(
            "Command %s is not executable" % cmd,
            str(ctx.exception))

    def test_as_environment(self):
        opts = dict(cmd="/bin/bash", repository_name="My repo")
        obj = SignOptions(**opts)
        # This is possible, whether a good idea or not.
        obj.extra = "foo"
        self.assertEqual(
            dict(GPG_CMD=opts['cmd'],
                 GPG_REPOSITORY_NAME=opts['repository_name'],
                 GPG_EXTRA="foo"),
            obj.as_environment())


class SignFileTest(SignerBaseTest):

    @base.mock.patch('debpkgr.signer.Signer.sign')
    def test_sign_debpkg(self, _sign):
        debpkg = self.mkfile("foo-0.0.1.deb", contents="Name: Foo")
        sign_file(debpkg, self.sign_cmd, self.key_id)
        _sign.assert_called_once_with(debpkg)
        pass
