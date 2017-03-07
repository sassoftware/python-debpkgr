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
from debian import deb822
from debpkgr.debpkg import DebPkg
from debpkgr.debpkg import DebPkgFiles
from debpkgr.debpkg import DebPkgMD5sums
from debpkgr.debpkg import DebPkgRequires
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
        # Make sure the hashes are not part of the control file
        for k in pkg.hashes:
            self.assertFalse(k in pkg._c)
        self.assertEquals(pkg.package, self.package_obj)
        # Make sure the hashes are still not part of the control file
        for k in pkg.hashes:
            self.assertFalse(k in pkg._c)
        self.assertTrue(isinstance(pkg.control, deb822.Deb822))
        self.assertTrue(isinstance(pkg.hashes, deb822.Deb822))

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

    def test_pkg_requires(self):
        TestData = namedtuple("TestData", "field data expected")

        ArchRestriction = namedtuple('ArchRestriction',
                                     ['enabled', 'arch'])
        defaults = dict([('depends', []),
                         ('pre_depends', []),
                         ('recommends', []),
                         ('suggests', []),
                         ('breaks', []),
                         ('conflicts', []),
                         ('provides', []),
                         ('replaces', []),
                         ('enhances', [])])

        empty = DebPkgRequires()
        self.assertTrue(defaults, empty)

        version_string = (u'foo (<<3.0-4), bar (<=1.5-0), baz (=1.2.0)'
                          ', caz (>= 1.0-6), cuz (>>4.0.0-1)')
        version_expect = [[{'arch': None,
                            'archqual': None,
                            'name': u'foo',
                            'restrictions': None,
                            'version': (u'<<', u'3.0-4')}],
                          [{'arch': None,
                            'archqual': None,
                            'name': u'bar',
                            'restrictions': None,
                            'version': (u'<=', u'1.5-0')}],
                          [{'arch': None,
                            'archqual': None,
                            'name': u'baz',
                            'restrictions': None,
                            'version': (u'=', u'1.2.0')}],
                          [{'arch': None,
                            'archqual': None,
                            'name': u'caz',
                            'restrictions': None,
                            'version': (u'>=', u'1.0-6')}],
                          [{'arch': None,
                            'archqual': None,
                            'name': u'cuz',
                            'restrictions': None,
                            'version': (u'>>', u'4.0.0-1')}]]

        wildcard_string = u'foo [linux-any], bar [any-i386], baz [!linux-any]'
        wildcard_expect = [[{'arch': [
            ArchRestriction(
                enabled=True,
                arch=u'linux-any')],
            'archqual': None,
            'name': u'foo',
            'restrictions': None,
            'version': None}],
            [{'arch': [
                ArchRestriction(
                    enabled=True,
                    arch=u'any-i386')],
              'archqual': None,
              'name': u'bar',
              'restrictions': None,
              'version': None}],
            [{'arch': [
                ArchRestriction(
                    enabled=False,
                    arch=u'linux-any')],
              'archqual': None,
              'name': u'baz',
              'restrictions': None,
              'version': None}]]
        arch_string = u'fuz [!amd64], caz [i386], cuz [amd64], daz [!i386]'
        arch_expect = [[{'arch': [
            ArchRestriction(
                enabled=False,
                arch=u'amd64')],
            'archqual': None,
            'name': u'fuz',
            'restrictions': None,
            'version': None}],
            [{'arch': [
                ArchRestriction(
                    enabled=True,
                    arch=u'i386')],
                'archqual': None,
                'name': u'caz',
              'restrictions': None,
              'version': None}],
            [{'arch': [
                ArchRestriction(
                    enabled=True,
                    arch=u'amd64')],
                'archqual': None,
                'name': u'cuz',
              'restrictions': None,
              'version': None}],
            [{'arch': [
                ArchRestriction(
                    enabled=False,
                    arch=u'i386')],
                'archqual': None,
                'name': u'daz',
              'restrictions': None,
              'version': None}]]
        alternative_string = (u'baz2.7 | baz3.5, buz [i386] | fuz [amd64]'
                              ', foo [linux-any] | fuz [linux-i386]')

        alternative_expect = [[{'arch': None,
                                'archqual': None,
                                'name': u'baz2.7',
                                'restrictions': None,
                                'version': None},
                               {'arch': None,
                                'archqual': None,
                                'name': u'baz3.5',
                                'restrictions': None,
                                'version': None}],
                              [{'arch': [
                                  ArchRestriction(
                                      enabled=True,
                                      arch=u'i386')],
                                  'archqual': None,
                                  'name': u'buz',
                                'restrictions': None,
                                'version': None},
                               {'arch': [
                                   ArchRestriction(
                                       enabled=True,
                                       arch=u'amd64')],
                                  'archqual': None,
                                  'name': u'fuz',
                                  'restrictions': None,
                                  'version': None}],
                              [{'arch': [
                                  ArchRestriction(
                                      enabled=True,
                                      arch=u'linux-any')],
                                  'archqual': None,
                                  'name': u'foo',
                                  'restrictions': None,
                                  'version': None},
                               {'arch': [
                                   ArchRestriction(
                                       enabled=True,
                                       arch=u'linux-i386')],
                                  'archqual': None,
                                  'name': u'fuz',
                                  'restrictions': None,
                                  'version': None}]]

        tests = [TestData('Depends', version_string, version_expect),
                 TestData('Breaks', wildcard_string, wildcard_expect),
                 TestData('Conflicts', arch_string, arch_expect),
                 TestData('Suggests', alternative_string, alternative_expect),
                 ]

        for td in tests:
            control_data = self.control_data.copy()
            control_data.update({td.field: td.data})
            requires = DebPkgRequires(**control_data)
            if td.field == 'Depends':
                self.assertTrue(td.expected, requires.depends)
            else:
                self.assertTrue(td.expected, requires.relations[
                                td.field.lower()])

    def test_pkg_dependencies(self):
        ArchRestriction = namedtuple('ArchRestriction',
                                     ['enabled', 'arch'])
        # TODO
        # BuildRestriction = namedtuple('BuildRestriction',
        #                              ['enabled', 'profile'])
        control_data = self.control_data.copy()
        control_data.update({'Breaks': u'broken (<=1.0-1) [i386]',
                             'Conflicts': u'conflicting (=1.0-4)',
                             'Pre-Depends': u'pre (>= 2.0-1)',
                             'Depends': u'bar (>= 1.0-6), baz2.7 | baz3.5, '
                             'buz [i386] | fuz [amd64], '
                             'caz [i386], cuz [amd64], '
                             'daz [!i386]',
                             'Enhances': u'enhanceable [!i386]',
                             })

        dependencies = {u'breaks': [[{'arch':
                                      [ArchRestriction(
                                          enabled=True, arch=u'i386')],
                                      'archqual': None,
                                      'name': u'broken',
                                      'restrictions': None,
                                      'version': (u'<=', u'1.0-1')}]],
                        u'conflicts': [[{'arch': None,
                                         'archqual': None,
                                         'name': u'conflicting',
                                         'restrictions': None,
                                         'version': (u'=', u'1.0-4')}]],
                        u'depends': [[{'arch': None,
                                       'archqual': None,
                                       'name': u'bar',
                                       'restrictions': None,
                                       'version': (u'>=', u'1.0-6')}],
                                     [{'arch': None,
                                       'archqual': None,
                                       'name': u'baz2.7',
                                       'restrictions': None,
                                       'version': None},
                                      {'arch': None,
                                         'archqual': None,
                                         'name': u'baz3.5',
                                         'restrictions': None,
                                         'version': None}],
                                     [{'arch':
                                       [ArchRestriction(
                                           enabled=True, arch=u'i386')],
                                       'archqual': None,
                                       'name': u'buz',
                                       'restrictions': None,
                                       'version': None},
                                      {'arch':
                                         [ArchRestriction(
                                             enabled=True, arch=u'amd64')],
                                       'archqual': None,
                                       'name': u'fuz',
                                       'restrictions': None,
                                       'version': None}],
                                     [{'arch':
                                       [ArchRestriction(
                                           enabled=True, arch=u'i386')],
                                         'archqual': None,
                                       'name': u'caz',
                                       'restrictions': None,
                                       'version': None}],
                                     [{'arch':
                                       [ArchRestriction(
                                           enabled=True, arch=u'amd64')],
                                         'archqual': None,
                                       'name': u'cuz',
                                       'restrictions': None,
                                       'version': None}],
                                     [{'arch':
                                       [ArchRestriction(
                                           enabled=False, arch=u'i386')],
                                         'archqual': None,
                                       'name': u'daz',
                                       'restrictions': None,
                                       'version': None}]],
                        u'enhances': [[{'arch':
                                        [ArchRestriction(
                                            enabled=False, arch=u'i386')],
                                        'archqual': None,
                                        'name': u'enhanceable',
                                        'restrictions': None,
                                        'version': None}]],
                        u'pre_depends': [[{'arch': None,
                                           'archqual': None,
                                           'name': u'pre',
                                           'restrictions': None,
                                           'version': (u'>=', u'2.0-1')}]],
                        u'provides': [],
                        u'recommends': [],
                        u'replaces': [],
                        u'suggests': []}

        pkg = DebPkg(control_data, self.md5sum_data, self.hashes_data)
        self.assertEquals(dependencies, pkg.dependencies)
        self.assertEquals(dependencies['depends'], pkg.depends)

    @base.mock.patch("debpkgr.debpkg.debfile.DebFile")
    def test_pkg_from_file(self, _DebFile):
        meta = dict(package="a", version="1", architecture="amd64")
        _DebFile.return_value.control.debcontrol.return_value = meta
        dp = DebPkg.from_file("/dev/null")
        # Let's convert the rfc822 format to a dict
        lines = str(dp.package).split('\n')
        ldict = dict((x, z) for (x, y, z) in
                     (line.partition(': ') for line in lines))
        # Make sure the original dict is included
        for k, v in meta.items():
            self.assertEquals(v, ldict[k])

    @base.mock.patch("debpkgr.debpkg.debfile.DebFile")
    def test_pkg_from_file_with_Filename(self, _DebFile):
        _DebFile.return_value.control.debcontrol.return_value = {}
        Filename = "pool/comp/a_1.deb"
        dp = DebPkg.from_file("/dev/null", Filename=Filename)
        self.assertEquals(Filename, dp._c['Filename'])
