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
import time
from datetime import datetime, timedelta, tzinfo
from io import BytesIO

from six import PY3

from debpkgr.aptrepo import AptRepoMeta, AptRepo, create_repo, deb822
from tests import base


class MockBytesIO(BytesIO):

    def close(self):
        pass


class FixedOffset(tzinfo):

    """Fixed offset in minutes: `time = utc_time + utc_offset`."""

    def __init__(self, offset):
        self.__offset = timedelta(minutes=offset)
        hours, minutes = divmod(offset, 60)
        # NOTE: the last part is to remind about
        #  deprecated POSIX GMT+h timezones
        #  that have the opposite sign in the name;
        #  the corresponding numeric value is not used e.g., no minutes
        self.__name = '<%+03d%02d>%+d' % (hours, minutes, -hours)

    def utcoffset(self, dt=None):
        return self.__offset

    def tzname(self, dt=None):
        return self.__name

    def dst(self, dt=None):
        return timedelta(0)

    def __repr__(self):
        return 'FixedOffset(%d)' % (self.utcoffset().total_seconds() / 60)


class RepoTest(base.BaseTestCase):

    def setUp(self):
        base.BaseTestCase.setUp(self)
        self.name = 'unit_test_repo_foo'  # should match Origin and Label
        self.components = ['main', 'updates']
        self.arches = ['amd64', 'i386', 'aarch64']
        self.repoversion = '2.0'
        self.description = 'Apt repository for Unit Test Repo Foo'
        self.timestamp = time.strftime('%a, %d %b %Y %H:%M:%S %z')

        self.date_format = u'Sat, 02 Jul 2016 05:20:50 +0000'

        self.repodir = u'dists/stable'

        self.bindirs = [u'dists/stable/main/binary-amd64',
                        u'dists/stable/updates/binary-amd64',
                        u'dists/stable/main/binary-i386',
                        u'dists/stable/updates/binary-i386',
                        u'dists/stable/main/binary-aarch64',
                        u'dists/stable/updates/binary-aarch64']

        self.pools = [u'pool/main', u'pool/updates']

        self.directories = self.bindirs + self.pools

        self.defaults = {'origin': self.name,
                         'label': self.name,
                         'version': self.repoversion,
                         'description': self.description,
                         'codename': 'stable',
                         'components': self.components,
                         'architectures': self.arches,
                         'archives': {},  # path : deb822 pkg
                         'packages': {},
                         'releases': {},
                         }

        file_names = ['foo_0.0.1-1_amd64.deb',
                      'foo_0.0.1-1_i386.deb',
                      'foo_0.0.1-1_aarch64.deb',
                      'bar_0.1.1-1_amd64.deb',
                      'bar_0.1.1-1_i386.deb',
                      'bar_0.1.1-1_aarch64.deb',
                      'buz_0.2.1-1_amd64.deb',
                      'buz_0.2.1-1_i386.deb',
                      'buz_0.2.1-1_aarch64.deb',
                      ]
        self.files = [self.mkfile(x, contents=x) for x in file_names]

        self.hashdict = [{'md5sum': ['62dfc288d6b0dee2b157b6de1ad8db3a',
                                     '538',
                                     'main/binary-amd64/Packages'],
                          'sha1': ['6935649933c0748e05ea909875707c0308db1c8f',
                                   '538',
                                   'main/binary-amd64/Packages'],
                          'sha256': ['9099749f2ae75a45c848c414ce416d03b'
                                     '803c2abb01a775ed37ec885877109c2',
                                     '538',
                                     'main/binary-amd64/Packages']},
                         {'md5sum': ['5b4c18786ef6c01d694d0911a3f3576f',
                                     '409',
                                     'main/binary-amd64/Packages.gz'],
                          'sha1': ['3785ac8d4c371dc2c1d2bcb29deef458fb453cc8',
                                   '409',
                                   'main/binary-amd64/Packages.gz'],
                          'sha256': ['58ad2a8e3952e6fe8e467fed5c890dbc684781'
                                     '499587c61969a5255059bc9e2e',
                                     '409',
                                     'main/binary-amd64/Packages.gz']},
                         ]

        self.release_data = {'Origin': u'unit_test_repo_foo',
                             'Architecture': u'amd64',
                             'Component': u'main',
                             'Description':
                             u'Apt repository for Unit Test Repo Foo',
                             'Label': u'unit_test_repo_foo'}

        self.repo_release_data = {'Origin': u'unit_test_repo_foo',
                                  'Label': u'unit_test_repo_foo',
                                  'Description':
                                  u'Apt repository for Unit Test Repo Foo',
                                  'Version': u'2.0',
                                  'Architectures': u'amd64 i386 aarch64',
                                  'Components': u'main updates',
                                  'Suite': u'stable',
                                  'Codename': u'stable',
                                  }

        self.sha1sums = {
            'SHA1': [{'sha1': u'6935649933c0748e05ea909875707c0308db1c8f',
                      'size': u'538',
                      'name': u'main/binary-amd64/Packages'},
                     {'sha1': u'3785ac8d4c371dc2c1d2bcb29deef458fb453cc8',
                      'size': u'409',
                      'name': u'main/binary-amd64/Packages.gz'}]}
        self.md5sums = {
            'MD5Sum': [{'md5sum': u'62dfc288d6b0dee2b157b6de1ad8db3a',
                        'size': u'538',
                        'name': u'main/binary-amd64/Packages'},
                       {'md5sum': u'5b4c18786ef6c01d694d0911a3f3576f',
                        'size': u'409',
                        'name': u'main/binary-amd64/Packages.gz'}]}
        self.sha256sums = {
            'SHA256': [{'sha256': u'9099749f2ae75a45c848c414ce416d03b'
                        '803c2abb01a775ed37ec885877109c2',
                        'size': u'538',
                        'name': u'main/binary-amd64/Packages'},
                       {'sha256': '58ad2a8e3952e6fe8e467fed5c890dbc684'
                        '781499587c61969a5255059bc9e2e',
                        'size': u'409',
                        'name': u'main/binary-amd64/Packages.gz'}]}

    def test_metadata(self):
        repo_meta = AptRepoMeta(**self.defaults)

        self.assertEquals(repo_meta.repodir, self.repodir)
        self.assertEquals(repo_meta.pools, self.pools)
        self.assertEquals(repo_meta.bindirs, self.bindirs)
        self.assertEquals(repo_meta.directories, self.directories)

        release_content = repo_meta.make_release(
            self.components[0], self.arches[0])
        self.assertEquals(release_content, self.release_data)
        repo_release_content = repo_meta.make_repo_release(self.hashdict)
        for k, v in self.repo_release_data.items():
            self.assertEquals(repo_release_content[k], v)
        for k, v in self.sha1sums.items():
            for x in repo_release_content[k]:
                self.assertTrue(x['sha1'] in [y['sha1']
                                              for y in self.sha1sums[k]])
                self.assertTrue(x['size'] in [y['size']
                                              for y in self.sha1sums[k]])
                self.assertTrue(x['name'] in [y['name']
                                              for y in self.sha1sums[k]])
        for k, v in self.md5sums.items():
            for x in repo_release_content[k]:
                self.assertTrue(x['md5sum'] in [y['md5sum']
                                                for y in self.md5sums[k]])
        for k, v in self.sha256sums.items():
            for x in repo_release_content[k]:
                self.assertTrue(x['sha256'] in [y['sha256']
                                                for y in self.sha256sums[k]])

        # Because Python2 does not support %z
        test_date = repo_release_content['Date']
        if PY3:
            time.strptime(test_date, '%a, %d %b %Y %H:%M:%S %z')
            self.assert_(True)
        else:
            test_date_str, _, test_offset_str = test_date.rpartition(' ')
            test_dt = datetime.strptime(test_date_str, '%a, %d %b %Y %H:%M:%S')
            offset = int(test_offset_str[-4:-2]) * 60 + int(
                test_offset_str[-2:])
            if test_offset_str[0] == "-":
                offset = -offset
            test_dt = test_dt.replace(tzinfo=FixedOffset(offset))
            self.assertEquals(
                test_date,
                test_dt.strftime('%a, %d %b %Y %H:%M:%S %z'))

        # assert release_content == False
    @base.mock.patch("debpkgr.aptrepo.debpkg.debfile")
    def test_AptRepo_create(self, _debfile):
        D = deb822.Deb822
        # We need to reorder the files alphabetically, so the way os.walk
        # finds them is the same as the mock we're setting up
        Files = [
            (D(dict(Package="bar", Architecture="aarch64", Version="0.1.1",
                    Release="1")), self.files[5]),
            (D(dict(Package="bar", Architecture="amd64", Version="0.1.1",
                    Release="1")), self.files[3]),
            (D(dict(Package="bar", Architecture="i386", Version="0.1.1",
                    Release="1")), self.files[4]),
            (D(dict(Package="foo", Architecture="aarch64", Version="0.1.1",
                    Release="1")), self.files[2]),
            (D(dict(Package="foo", Architecture="amd64", Version="0.1.1",
                    Release="1")), self.files[0]),
            (D(dict(Package="foo", Architecture="i386", Version="0.1.1",
                    Release="1")), self.files[1]),
        ]
        pkgs = [x[0] for x in Files]
        debcontrol = _debfile.DebFile.return_value.control.debcontrol
        debcontrol.return_value.copy.side_effect = pkgs

        blacklist = ['origin', 'label']
        defaults = dict((k, v) for k, v in self.defaults.items()
                        if k not in blacklist)
        defaults['components'] = ['main']
        defaults['architectures'] = ['amd64', 'i386']
        repo = AptRepo(self.new_repo_dir, self.name, **defaults)
        self.assertEquals(repo.repo_name, self.name)
        repo.create([x[1] for x in Files], with_symlinks=True)

        pool_files = [os.path.join(self.new_repo_dir, "pool", "main",
                                   os.path.basename(x))
                      for x in sorted(y[1] for y in Files)]
        self.assertEquals(
            [base.mock.call(filename=x) for x in pool_files],
            _debfile.DebFile.call_args_list)
        # Make sure Size and Filename are part of the debcontrol
        # The contents of the files are the filenames, so it is easy to check
        # the file size
        self.assertEquals(
            [(os.path.join("pool", "main", os.path.basename(x)),
              str(len(os.path.basename(x))))
             for x in sorted(y[1] for y in Files)],
            [(x[0]['Filename'], x[0]['Size']) for x in Files])

        # Make sure we have some Packages files
        dist_dir = os.path.join(self.new_repo_dir, "dists", "stable", "main")
        self.assertFalse(os.path.exists(
            os.path.join(dist_dir, 'binary-aarch64')))
        for exp, arch, idx in [(544, 'amd64', [1, 4]), (540, 'i386', [2, 5])]:
            path = os.path.join(dist_dir, 'binary-%s' % arch, 'Packages')
            self.assertEquals(
                exp,
                os.stat(path).st_size)
            pkgs = [x for x in D.iter_paragraphs(open(path, "rb"))]

            exp_filenames = [
                os.path.join("pool", "main", os.path.basename(Files[i][1]))
                for i in idx]

            self.assertEquals(exp_filenames, [x['Filename'] for x in pkgs])

    @base.mock.patch("debpkgr.aptrepo.AptRepo")
    @base.mock.patch("debpkgr.aptrepo.AptRepo.create")
    def test_repo_create(self, _AptRepo, _create):
        repo = create_repo(self.new_repo_dir, self.files, name=self.name,
                           arches=None, desc=None, with_symlinks=False)
        self.assertEquals(_create.return_value, repo)
        _create.assert_called_once_with(self.new_repo_dir, self.name,
                                        architectures=None, description=None)
        repo.create.assert_called_once_with(self.files, with_symlinks=False)
