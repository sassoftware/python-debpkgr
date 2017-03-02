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

# flake8: noqa
try:
    import unittest2 as unittest
except ImportError:
    import unittest  # noqa

try:
    from unittest import mock  # noqa
except ImportError:
    import mock  # noqa


from tests import base
from debpkgr.main import apt_indexer
from debpkgr.main import deb_package


class MainTests(base.BaseTestCase):

    @mock.patch('debpkgr.main.apt_indexer')
    @mock.patch('debpkgr.aptrepo.create_repo')
    @mock.patch('sys.argv')
    def test_apt_indexer(self, _apt_indexer, _create_repo, _argv):
        test_args = ["-c", "-n", "esp_test_repo", "-a", "amd64",
                     "-D", "ESP Test APT Repo for Debian",
                     "pool/main/foo.deb", "pool/main/bar.deb",
                     "pool/main/buz.deb"]
        _argv.results = test_args
        _create_repo.results = {}
        _apt_indexer()
        _apt_indexer.called_with(test_args)

    @mock.patch('debpkgr.main.deb_package')
    @mock.patch('debpkgr.debpkg')
    @mock.patch('sys.argv')
    def test_deb_package(self, _deb_package, _debpkg, _argv):
        test_args = ["-p", "pool/main/foo_0.0.1-1_amd64.deb"]
        _argv.results = test_args
        _deb_package()
        _deb_package.called_with(test_args)
