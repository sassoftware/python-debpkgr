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

from collections import namedtuple

from debpkgr import hasher

from tests import base


class HashData(namedtuple("HashData", "data algs expected")):

    """
    HashData Class
    """


class HasherTests(base.BaseTestCase):

    def setUp(self):
        base.BaseTestCase.setUp(self)
        self.data = u"Unchained, yeah ya hit the ground running"
        self.expected = {'sha256':
                         'b96eda7b0c56640a48644ae1651129d496aa25934ed9'
                         '2dc7b597f927c37e80b8',
                         'md5': '765bfe8283c21e663e5b9b4b86037bb0',
                         'sha1': '952419509423d5da3fa00955ecff36d98d8c2e29'}
        self.algs = ["md5", "sha1", "sha256"]
        self.debian_keys = dict(zip(["MD5sum", "SHA1", "SHA256"], self.algs))

    def test_hash_from_file(self):

        tests = [HashData(self.data, self.algs, self.expected)]

        for td in tests:
            filename = os.path.join(self.test_dir, "hash_test.txt")
            with open(filename, 'w') as fh:
                fh.write(self.data)
            self.assertEqual(td.expected, hasher.hash_file(filename, td.algs))

    def test_debian_hash_from_file(self):

        tests = [HashData(self.data, self.algs, self.expected)]

        for td in tests:
            filename = os.path.join(self.test_dir, "deb_hash_test.txt")
            with open(filename, 'w') as fh:
                fh.write(self.data)
            digests = hasher.deb_hash_file(filename)
            for k, v in digests.items():
                self.assertEqual(td.expected[self.debian_keys[k]], v)

    def test_hash_from_string(self):

        tests = [
            HashData(self.data, ["md5"],
                     {"md5": "765bfe8283c21e663e5b9b4b86037bb0"}),
            HashData(self.data, ["sha1"],
                     {"sha1": "952419509423d5da3fa00955ecff36d98d8c2e29"}),
        ]
        for td in tests:
            self.assertEqual(td.expected, hasher.hash_string(td.data, td.algs))
