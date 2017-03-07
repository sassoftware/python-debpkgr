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

from collections import namedtuple

from debpkgr import errors

from tests import base


class ErrorTests(base.BaseTestCase):

    def raise_error(self, exception, msg):
        raise exception(msg)

    def raise_error_check(self, exception, msg):
        with self.assertRaises(exception) as context:
            self.raise_error(exception, msg)
        self.assertTrue(msg in str(context.exception))

    def test_errors(self):
        TestData = namedtuple("TestData", "err msg")
        tests = [TestData(errors.DebPkgError, u'Base Error'),
                 TestData(errors.InvalidTest, u'Invalid test error'),
                 TestData(errors.SourceBuildError, u'Source build error'),
                 TestData(errors.BinaryBuildError, u'Binary build error'),
                 TestData(errors.InvalidKeyError, u'Invalid key error'),
                 TestData(errors.KeyNotFoundError, u'Key not found error'),
                 ]
        for td in tests:
            self.raise_error_check(td.err, td.msg)
