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

from debpkgr import utils

from tests import base


class UtilsTests(base.BaseTestCase):

    def test_local_path_from_url(self):
        TestData = namedtuple("TestData", "data expected")

        tests = [TestData("a", "a"),
                 TestData("/a", "/a"),
                 TestData("/a/b", "/a/b"),
                 TestData("file://a", "a"),
                 TestData("file://a/b", "a/b"),
                 TestData("file:///a", "/a"),
                 TestData("file:///a/b", "/a/b"),
                 TestData("http://a:1024", None),
                 TestData("ftp://a", None),
                 ]
        for td in tests:
            self.assertEqual(td.expected, utils.local_path_from_url(td.data))

    def test_normalize_paths(self):
        TestPath = namedtuple("TestPath", "data expected")
        tests = [TestPath(u"file:////a",
                          os.path.join(self.test_dir, 'file:/a')),
                 TestPath(u"/usr/../data", "/data"),
                 TestPath(u"debian//control.tar.gz",
                          os.path.join(
                              self.test_dir, "debian/control.tar.gz")),
                 ]
        for td in tests:
            self.assertEqual(td.expected, utils.normpath(td.data))

    def test_normalize_env_names(self):
        TestEnv = namedtuple("TestEnv", "data expected")
        tests = [TestEnv(u"Hey, man, that Suit is you!Ted",
                         u"HEY_MAN_THAT_SUIT_IS_YOU_TED"),
                 TestEnv(u"Dave, give me a break",
                         u"DAVE_GIVE_ME_A_BREAK")]
        for td in tests:
            self.assertEqual(td.expected, utils.normenvname(td.data))
