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

'''
Python Methods for signing Debian Repository and .deb Files
'''

from __future__ import absolute_import
from __future__ import unicode_literals

import logging
import os
import tempfile
import shlex
import subprocess

log = logging.getLogger(__name__)


class SignerError(Exception):

    def __init__(self, *args, **kwargs):
        self.stdout = kwargs.pop('stdout', None)
        self.stderr = kwargs.pop('stderr', None)
        super(SignerError, self).__init__(*args, **kwargs)


class SignOptions(object):
    """
    An object to configure the gpg signer.

    A cmd is expected to be passed into the object. That is the command to
    execute in order to sign the file.

    The command should accept one argument, a path to a file.

    This class' fields, prepended with GPG_ and upper-cased, will be
    presented to the command as environment variables. The
    command may determine which gpg key to use based on GPG_KEY_ID
    or GPG_REPOSITORY_NAME
    """

    def __init__(self, cmd=None, key_id=None, **kwargs):
        if not cmd:
            raise SignerError("Command not specified")
        self.cmd = cmd
        self._cmdargs = shlex.split(cmd)
        if not os.path.isfile(self._cmdargs[0]):
            raise SignerError(
                "Command %s is not a file" % (self._cmdargs[0], ))
        if not os.access(self._cmdargs[0], os.X_OK):
            raise SignerError("Command %s is not executable" %
                              (self._cmdargs[0], ))

        self.key_id = key_id
        self.repository_name = None
        self.dist = None
        self.extra = None

        for k, v in kwargs.items():
            setattr(self, k, v)

    def as_environment(self):
        env_dict = dict()
        for k in self.__dict__:
            v = getattr(self, k)
            if k.startswith('_') or v is None:
                continue
            k = k.replace('-', '_').upper()
            env_dict['GPG_%s' % k] = str(v)
        return env_dict


class Signer(object):
    """
    An object that implements signing

    The options object should be an instance of SignOptions class

    Example:
      kwargs = dict(repository_name='foo',dist='stable',random_env_var='bar')
      options = SignOptions(cmd=cmd, key_id=key_id, **kwargs)
      signer = Signer(options=options)
      signer.sign(path)

    sign method returns (stdout, stderr)

    """

    def __init__(self, options=None):
        if options is not None:
            if not isinstance(options, SignOptions):
                raise ValueError(
                    "Signer options: unexpected type %r" %
                    (options, ))
        self.options = options

    def sign(self, path):
        if not self.options:
            return
        cmd = self.options._cmdargs
        cmd.append(path)
        stdout = tempfile.NamedTemporaryFile()
        stderr = tempfile.NamedTemporaryFile()
        pobj = subprocess.Popen(
            cmd, env=self.options.as_environment(),
            stdout=stdout, stderr=stderr)
        ret = pobj.wait()
        if ret != 0:
            raise SignerError("Return code: %d" % ret,
                              stdout=stdout, stderr=stderr)
        return stdout, stderr


def sign_file(path, cmd, key_id, **kwargs):
    options = SignOptions(cmd=cmd, key_id=key_id, **kwargs)
    signer = Signer(options=options)
    return signer.sign(path)
