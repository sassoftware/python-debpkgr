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
import functools
import os
import tempfile

from debpkgr.aptrepo import create_repo
from debpkgr.aptrepo import parse_repo
from debpkgr.aptrepo import index_repo
from tests import base

class CreateRepoTest(base.BaseTestCase):

    def test_create_repo(self):
        name = 'test_repo_foo' # should match Origin and Label
        arches = [ 'amd64', 'i386' ]
        description = 'Apt repository for Test Repo Foo'
        files = [os.path.join(self.pool_dir, x)
                  for x in os.listdir(self.pool_dir) if x.endswith('.deb')]
        repo = create_repo(self.new_repo_dir, files, name=name, 
                                arches=arches, desc=description)
        

    def X_test_index_repo(self):
        repo = index_repo(self.new_repo_dir)

    def X_test_parse_repo(self):
        repo = parse_repo(self.current_repo_dir)
