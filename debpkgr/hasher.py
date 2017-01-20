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
import six
import hashlib


class Hasher(object):

    def __init__(self, algorithms=None):
        if isinstance(algorithms, six.string_types):
            algorithms = [algorithms]
        if not algorithms:
            algorithms = self._available_algorithms()
        self.algorithms = set(algorithms)
        self.hashers = self._digests = None
        self.reset()

    def reset(self):
        self.hashers = dict([(x, getattr(hashlib, x)())
                            for x in self._available_algorithms()
                            if x in self.algorithms])
        self._digests = None

    def update(self, data):
        """
        Update all hashers with (the byte-array) data.
        Unicode strings and Python 3 strings will need to be encoded before
        passing them to this function.
        """
        if not data:
            return
        # Invalidate computed digests
        self._digests = None
        for hasher in self.hashers.values():
            hasher.update(data)

    def _available_algorithms(self):
        if not hasattr(hashlib, 'algorithms_guaranteed'):
            # Debian's python 2.7.6 does not have it
            return hashlib.algorithms
        return hashlib.algorithms_guaranteed

    def _hash(self, hasher):
        raise NotImplementedError

    def _make_hashes(self):
        if None in self._digests.values():
            for k, hasher in self.hashers.items():
                self._digests[k] = self._hash(hasher())

    @property
    def available(self):
        return self.algorithms

    @property
    def digests(self):
        if self._digests is None:
            self._digests = dict((x, y.hexdigest())
                                 for (x, y) in self.hashers.items())
        return self._digests

    def read(self):
        raise NotImplementedError


class HashString(Hasher):

    def __init__(self, data, algorithms=None):
        if hasattr(data, "encode"):
            data = data.encode('utf-8')
        super(HashString, self).__init__(algorithms=algorithms)
        self.update(data)


class HashFile(object):
    BLOCKSIZE = 65536

    def __init__(self, path, algorithms=None):
        self.path = path
        self.filename = os.path.basename(self.path)
        self.digest_path = '.'.join([self.path, 'chksums'])
        self.hasher = Hasher(algorithms=algorithms)
        self._digests = None

    @property
    def digests(self):
        if self._digests is None:
            with open(self.path, 'rb') as fh:
                while True:
                    buf = fh.read(self.BLOCKSIZE)
                    if not buf:
                        break
                    self.hasher.update(buf)
            self._digests = self.hasher.digests
        return self._digests

    @property
    def digest_lines(self):
        '''
        BSD Style for use in single file
        '''
        digests = self.digests
        lines = []
        template = "{0} ({1}) = {2}"
        for k, v in sorted(digests.items()):
            lines.append(template.format(k.capitalize(), self.filename, v))
        return lines

    def write(self):
        with open(self.digest_path, 'w') as fh:
            for line in sorted(self.digest_lines):
                fh.write(line)
                fh.write('\n')
        return self.digest_path

# UTILS


def hash_file(path, algs=['md5', 'sha1', 'sha256']):
    hasher = HashFile(path, algorithms=algs)
    return hasher.digests


def deb_hash_file(path):
    '''
    Apt Package File uses different syntax
    '''
    translation = dict(md5="MD5sum", sha1="SHA1", sha256="SHA256")
    digests = hash_file(path, algs=translation.keys())
    # Use the "translated" strings for keys
    hashes = dict((translation[x], y) for (x, y) in digests.items())
    return hashes


def hash_string(data, algs=['md5', 'sha1', 'sha256']):
    hasher = HashString(data, algorithms=algs)
    return hasher.digests
