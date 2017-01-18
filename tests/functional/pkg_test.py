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

from debian import deb822
from debpkgr.debpkg import DebPkg
from debpkgr.debpkg import DebPkgFiles
from debpkgr.debpkg import DebPkgMD5sums
from tests import base


class PkgTest(base.BaseTestCase):

    def test_pkg(self):

        package_data = {'Package': u'foo',
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
                        'MD5sum': u'5fc5c0cb24690e78d6c6a2e13753f1aa',
                        'SHA256': u'd80568c932f54997713bb7832c6da6aa04992919'
                        'f3d0f47afb6ba600a7586780',
                        'SHA1': u'5e26ae3ebf9f7176bb7fd01c9e802ac8e223cdcc'
                        }

        attrs_data = {'md5sum': u'5fc5c0cb24690e78d6c6a2e13753f1aa',
                      'sha1': u'5e26ae3ebf9f7176bb7fd01c9e802ac8e223cdcc',
                      'sha256': u'd80568c932f54997713bb7832c6da6aa049929'
                              '19f3d0f47afb6ba600a7586780',
                      'name': u'foo',
                      'nvra': u'foo_0.0.1-1_amd64',
                      }

        md5sums_data = {u'usr/share/doc/foo/changelog.Debian.gz':
                        u'9e2d1b5db1f1fb50621a48538d570ee8',
                        u'usr/share/doc/foo/copyright':
                        u'a664cb0d199e56bb5691d8ae29ca759a',
                        u'usr/share/doc/foo/README.Debian':
                        u'22c9f74e69fd45c5a60331586763c253'}

        files_data = [x for x in md5sums_data.keys()]

        package_attrs = {'foo': attrs_data}
        package_objects = {'foo': deb822.Deb822(package_data)}
        package_files = {'foo': DebPkgFiles(files_data)}
        package_md5sums = {'foo': DebPkgMD5sums(md5sums_data)}

        files = []
        for root, _, fl in os.walk(self.pool_dir):
            for f in fl:
                if f.endswith('.deb'):
                    files.append(os.path.join(root, f))

        packages = {}

        for fpath in files:
            pkg = DebPkg.from_file(fpath)
            packages.setdefault(pkg.name, pkg)

        for name, pkg in packages.items():
            if name in package_attrs:
                for attr in package_attrs[name]:
                    self.assertEquals(package_attrs[name][attr],
                                      getattr(pkg, attr))
            if name in package_md5sums:
                self.assertEquals(package_md5sums[name], pkg.md5sums)
            if name in package_files:
                self.assertEquals(sorted([x for x in package_files[name]]),
                                  sorted([x for x in pkg.files]))
                self.assertEquals(package_files[name], pkg.files)
            if name in package_data:
                self.assertEquals(package_objects[name], pkg.package)
