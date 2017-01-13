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
import os
import shutil
import pkg_resources
import tempfile
import unittest

from six import text_type


try:
    import unittest2 as unittest
except ImportError:
    import unittest

try:
    from unittest import mock  # noqa
except ImportError:
    import mock  # noqa


class BaseTestCase(unittest.TestCase):
    test_dir_pre = 'debpkgr-test-'

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix=self.test_dir_pre)
        self.current_repo_dir = os.path.join(self.test_dir, 'cur_repo')
        self.new_repo_dir = self.mkdir('new_repo')
        self.pool_dir = os.path.join(self.current_repo_dir, 'pool', 'main')
                

        test_data = pkg_resources.resource_filename(
            __name__, 'test_data/')
        print(test_data)

        shutil.copytree(test_data, self.current_repo_dir)

        os.chdir(self.test_dir)

        self.addCleanup(shutil.rmtree, self.test_dir, ignore_errors=True)
        self.addCleanup(os.chdir, os.getcwd())

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
