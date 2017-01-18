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

from debian import deb822
from debpkgr.debpkg import DebPkg
from debpkgr.debpkg import DebPkgFiles
from debpkgr.debpkg import DebPkgMD5sums
from tests import base


class PkgTest(base.BaseTestCase):

    def setUp(self):
        self.control_data = {'Package': u'foo',
                             'Version': u'0.0.1-1',
                             'Architecture': u'amd64',
                             'Maintainer': u'Brett Smith <bc.smith@sas.com>',
                             'Installed-Size': u'25',
                             'Section': u'database',
                             'Priority': u'extra',
                             'Multi-Arch': u'foreign',
                             'Homepage': u'https://github.com/xbcsmith/foo',
                             'Description':
                             u'So this is the Foo of Brixton program\n'
                             ' When they kick at your front door\n How you'
                             ' gonna come?\n With your hands on your head\n'
                             ' Or on the trigger of your gun',
                             }

        self.md5sum_data = {
            'MD5sum': u'5fc5c0cb24690e78d6c6a2e13753f1aa',
            'SHA256': u'd80568c932f54997713bb7832c6da6aa04992919'
            'f3d0f47afb6ba600a7586780',
            'SHA1': u'5e26ae3ebf9f7176bb7fd01c9e802ac8e223cdcc'
        }

        self.hashes_data = {u'usr/share/doc/foo/changelog.Debian.gz':
                            u'9e2d1b5db1f1fb50621a48538d570ee8',
                            u'usr/share/doc/foo/copyright':
                            u'a664cb0d199e56bb5691d8ae29ca759a',
                            u'usr/share/doc/foo/README.Debian':
                            u'22c9f74e69fd45c5a60331586763c253'}

        self.files_data = sorted([x for x in self.hashes_data.keys()])

        self.md5sum_string = 'MD5sum 5fc5c0cb24690e78d6c6a2e13753f1aa\n'\
                             'SHA1 5e26ae3ebf9f7176bb7fd01c9e802ac8e223cdcc\n'\
                             'SHA256 d80568c932f54997713bb7832c6da6aa04992919'\
                             'f3d0f47afb6ba600a7586780\n'

        self.files_string = 'usr/share/doc/foo/README.Debian\n'\
                            'usr/share/doc/foo/changelog.Debian.gz\n'\
                            'usr/share/doc/foo/copyright'

        self.files_string_bad = 'usr/share/doc/foo/changelog.Debian.gz\n'\
            'usr/share/doc/foo/README.Debian\n'\
            'usr/share/doc/foo/copyright'

        # self.files_string = '\n'.join(self.files_data)
        self.attrs_data = {'md5sum': u'5fc5c0cb24690e78d6c6a2e13753f1aa',
                           'sha1': u'5e26ae3ebf9f7176bb7fd01c9e802ac8e223cdcc',
                           'sha256': u'd80568c932f54997713bb7832c6da6aa049929'
                           '19f3d0f47afb6ba600a7586780',
                           'name': u'foo',
                           'nvra': u'foo_0.0.1-1_amd64',
                           }

        self.package_data = self.control_data.copy()
        self.package_data.update(self.md5sum_data)

        self.package_obj = deb822.Deb822(self.package_data)

    def test_pkg(self):
        pkg = DebPkg(self.control_data, self.md5sum_data, self.hashes_data)
        for k, v in self.attrs_data.items():
            self.assertEquals(getattr(pkg, k), v)
        self.assertEquals(pkg.package, self.package_obj)
        # assert pkg == False

    def test_pkg_md5sums(self):
        md5sums = DebPkgMD5sums(self.md5sum_data)
        for k, v in self.md5sum_data.items():
            self.assertEquals(md5sums[k], v)
        self.assertEquals(str(md5sums), self.md5sum_string)
        # assert md5sums == False

    def test_pkg_files(self):
        files = DebPkgFiles(self.files_data)
        self.assertEquals([x for x in files], self.files_data)
        self.assertEquals(files, self.files_data)
        self.assertNotEquals(files, self.attrs_data)
        self.assertNotEquals(files, self.hashes_data)
        self.assertEquals(str(files), self.files_string)
        self.assertNotEquals(str(files), self.files_string_bad)
        # assert files == False
