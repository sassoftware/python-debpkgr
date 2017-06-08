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
from time import gmtime as orig_gmtime
from io import BytesIO

from debpkgr.aptrepo import AptRepoMeta, AptRepo
from debpkgr.aptrepo import create_repo, parse_repo
from debian import deb822
from debpkgr.signer import SignOptions, SignerError
from tests import base


class MockBytesIO(BytesIO):

    def close(self):
        pass


class RepoTest(base.BaseTestCase):

    def setUp(self):
        super(RepoTest, self).setUp()
        self.name = 'unit_test_repo_foo'  # should match Origin and Label
        self.components = ['main', 'updates']
        self.arches = ['amd64', 'i386', 'aarch64']
        self.repoversion = '2.0'
        self.description = 'Apt repository for Unit Test Repo Foo'

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

        self.checksums = {
            'SHA1': [{'sha1': u'6935649933c0748e05ea909875707c0308db1c8f',
                      'size': u'538',
                      'name': u'main/binary-amd64/Packages'},
                     {'sha1': u'3785ac8d4c371dc2c1d2bcb29deef458fb453cc8',
                      'size': u'409',
                      'name': u'main/binary-amd64/Packages.gz'}],
            'MD5Sum': [{'md5sum': u'62dfc288d6b0dee2b157b6de1ad8db3a',
                        'size': u'538',
                        'name': u'main/binary-amd64/Packages'},
                       {'md5sum': u'5b4c18786ef6c01d694d0911a3f3576f',
                        'size': u'409',
                        'name': u'main/binary-amd64/Packages.gz'}],
            'SHA256': [{'sha256': u'9099749f2ae75a45c848c414ce416d03b'
                        '803c2abb01a775ed37ec885877109c2',
                        'size': u'538',
                        'name': u'main/binary-amd64/Packages'},
                       {'sha256': '58ad2a8e3952e6fe8e467fed5c890dbc684'
                        '781499587c61969a5255059bc9e2e',
                        'size': u'409',
                        'name': u'main/binary-amd64/Packages.gz'}],
        }

    def test_metadata_get_component_arch_binary(self):
        repo_meta = AptRepoMeta(**self.defaults)
        with self.assertRaises(ValueError) as ctx:
            repo_meta.get_component_arch_binary('BOGUS', 'amd64')
        self.assertEquals(
            "Component BOGUS not supported (expected: main, updates)",
            str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            repo_meta.get_component_arch_binary('main', 'BOGUS')
        self.assertEquals(
            "Architecture BOGUS not defined (expected: amd64, i386, aarch64)",
            str(ctx.exception))

    @base.mock.patch("debpkgr.aptrepo.time.strftime")
    def test_metadata(self, _strftime):
        _strftime.return_value = "ABCDE"
        repo_meta = AptRepoMeta(**self.defaults)

        release_path = os.path.join(self.test_dir, 'dists', 'stable',
                                    'Release')
        self.assertEquals(release_path, repo_meta.release_path(self.test_dir))
        repo_meta.write_release(self.test_dir)

        expected = dict(self.repo_release_data, Date="ABCDE")
        self.assertEquals(expected,
                          deb822.Release(open(release_path, "rb").read()))

        comp_binary = repo_meta.get_component_arch_binary('main', 'amd64')
        release_path = os.path.join(self.test_dir, 'dists', 'stable',
                                    'main', 'binary-amd64', 'Release')
        self.assertEquals(release_path,
                          comp_binary.release_path(self.test_dir))
        comp_binary.write_release(self.test_dir)
        expected = self.release_data
        self.assertEquals(expected,
                          deb822.Release(open(release_path, "rb").read()))

    @base.mock.patch("debpkgr.aptrepo.time.strftime")
    def test_metadata_packages_from_release(self, _strftime):
        _strftime.return_value = "ABCDE"
        repo_meta = AptRepoMeta(**self.defaults)

        repo_meta.release.update(self.checksums)

        # SHA1 only for main/i386
        sha1sums = [
            dict(sha1="aaa", size="123", name="main/binary-i386/Pacakges.gz"),
            dict(sha1="bbb", size="456", name="main/binary-i386/Pacakges"),
        ]
        repo_meta.release.update(SHA1=sha1sums)

        ret = repo_meta.component_arch_binary_package_files_from_release()
        sha256sums = self.checksums['SHA256']
        expected = {
            ('main', 'amd64'): sha256sums,
            ('main', 'i386'): sha1sums,
        }

        self.assertEquals(expected, ret)

    def test_metadata_not_shared(self):
        # Make sure defaults are not shared between objects
        rel = deb822.Release(dict(Architectures="amd64 i386 aarch64"))
        md1 = AptRepoMeta(rel)
        self.assertEquals(['amd64', 'i386', 'aarch64'], md1.architectures)

        md1.architectures = ['amd64']
        self.assertEquals(['amd64'], md1.architectures)

        md2 = AptRepoMeta(rel)
        self.assertEquals(['amd64', 'i386', 'aarch64'], md2.architectures)

    @base.mock.patch("debpkgr.aptrepo.time.gmtime")
    def test_set_date(self, _gmtime):
        _gmtime.return_value = orig_gmtime(1234567890.123)
        repo_meta = AptRepoMeta(**self.defaults)

        self.assertEquals("Fri, 13 Feb 2009 23:31:30 +0000",
                          repo_meta.release['Date'])

    @base.mock.patch("debpkgr.aptrepo.debpkg.debfile")
    def test_AptRepo_create(self, _debfile):
        with_symlinks = True

        D = deb822.Deb822
        # We need to reorder the files alphabetically, so the way os.walk
        # finds them is the same as the mock we're setting up
        Files = [
            (D(dict(
                Package="bar", Architecture="amd64", Version="0.1.1-1")),
             self.files[3]),
            (D(dict(
                Package="bar", Architecture="i386", Version="0.1.1-1")),
             self.files[4]),
            (D(dict(
                Package="foo", Architecture="amd64", Version="0.0.1-1")),
             self.files[0]),
            (D(dict(
                Package="foo", Architecture="i386", Version="0.0.1-1")),
             self.files[1]),
        ]
        # Split files by arch
        separated = dict()
        for f in Files:
            arch = f[0]['Architecture']
            separated.setdefault(arch, []).append(f)
        src_files = []
        for arch, files in sorted(separated.items()):
            src_files.extend(files)

        pkgs = [x[0] for x in src_files]
        debcontrol = _debfile.DebFile.return_value.control.debcontrol
        debcontrol.return_value.copy.side_effect = pkgs

        blacklist = ['origin', 'label']
        defaults = dict((k, v) for k, v in self.defaults.items()
                        if k not in blacklist)
        defaults['components'] = ['main']
        defaults['architectures'] = ['amd64', 'i386']
        meta = AptRepoMeta(**defaults)
        repo = AptRepo(self.new_repo_dir, meta)
        self.assertEquals(defaults['codename'], repo.repo_name)

        for arch, files in sorted(separated.items()):
            fpaths = [x[1] for x in files]
            repo.add_packages(fpaths, component='main', architecture=arch,
                              with_symlinks=with_symlinks)

        repo.create(with_symlinks=with_symlinks)

        self.assertEquals(
            [base.mock.call(filename=x[1]) for x in src_files],
            _debfile.DebFile.call_args_list)
        pool_files = [os.path.join(self.new_repo_dir, "pool", "main",
                                   os.path.basename(x[1]))
                      for x in src_files]
        for src, dst in zip(src_files, pool_files):
            self.assertTrue(os.path.islink(dst))
            self.assertEquals(src[1], os.readlink(dst))
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

        for exp, arch, idx in [(525, 'amd64', [0, 2]), (521, 'i386', [1, 3])]:
            path = os.path.join(dist_dir, 'binary-%s' % arch, 'Packages')
            self.assertEquals(
                exp,
                os.stat(path).st_size)
            pkgs = [x for x in D.iter_paragraphs(open(path, "rb"))]

            exp_filenames = [
                os.path.join("pool", "main", os.path.basename(Files[i][1]))
                for i in idx]

            self.assertEquals(exp_filenames, [x['Filename'] for x in pkgs])

    @base.mock.patch("debpkgr.aptrepo.tempfile.NamedTemporaryFile")
    @base.mock.patch("debpkgr.signer.subprocess.Popen")
    def test_AptRepo_sign(self, _Popen, _NamedTemporaryFile):
        sign_cmd = self.mkfile("signme", contents="#!/bin/bash -e")
        os.chmod(sign_cmd, 0o755)
        so = SignOptions(cmd=sign_cmd)

        _Popen.return_value.wait.return_value = 0
        meta = AptRepoMeta(codename=self.name)
        repo = AptRepo(self.new_repo_dir, meta, gpg_sign_options=so)
        repo.sign("MyRelease")

        _Popen.assert_called_once_with(
            [sign_cmd, "MyRelease"],
            env=dict(
                GPG_CMD=sign_cmd,
                GPG_REPOSITORY_NAME="unit_test_repo_foo",
            ),
            stdout=_NamedTemporaryFile.return_value,
            stderr=_NamedTemporaryFile.return_value,
        )

    @base.mock.patch("debpkgr.aptrepo.tempfile.NamedTemporaryFile")
    @base.mock.patch("debpkgr.signer.subprocess.Popen")
    def test_AptRepo_sign_error(self, _Popen, _NamedTemporaryFile):
        sign_cmd = self.mkfile("signme", contents="#!/bin/bash -e")
        os.chmod(sign_cmd, 0o755)
        so = SignOptions(cmd=sign_cmd)

        _Popen.return_value.wait.return_value = 2
        meta = AptRepoMeta(codename=self.name)
        repo = AptRepo(self.new_repo_dir, metadata=meta,
                       gpg_sign_options=so)
        with self.assertRaises(SignerError) as ctx:
            repo.sign("MyRelease")
        self.assertEquals(
            _NamedTemporaryFile.return_value,
            ctx.exception.stdout)
        self.assertEquals(
            _NamedTemporaryFile.return_value,
            ctx.exception.stderr)

    def test_AptRepo_repo_name(self):
        meta = AptRepoMeta(codename='aaa')
        repo = AptRepo(self.new_repo_dir, metadata=meta)
        self.assertEquals('aaa', repo.repo_name)

        repo = AptRepo(self.new_repo_dir, metadata=meta, repo_name='bbb')
        self.assertEquals('bbb', repo.repo_name)

    @base.mock.patch("debpkgr.aptrepo.AptRepoMeta")
    @base.mock.patch("debpkgr.aptrepo.AptRepo")
    def test_repo_create(self, _AptRepo, _AptRepoMeta):
        repo = create_repo(self.new_repo_dir, self.files, name=self.name,
                           arches=None, desc=None, with_symlinks=False)
        aptrepo = _AptRepo.return_value
        self.assertEquals(aptrepo, repo)

        _AptRepo.assert_called_once_with(self.new_repo_dir,
                                         _AptRepoMeta.return_value)
        _AptRepoMeta.asset_called_once_with(codename=self.name,
                                            architectures=None,
                                            description=None)
        aptrepo.create.assert_called_once_with(
            self.files, with_symlinks=False)

    @base.mock.patch("debpkgr.aptrepo.AptRepo.parse")
    def test_repo_parse(self, _parse):
        upstream = base.mock.MagicMock()
        parse_repo(self.new_repo_dir, upstream, codename='stable')
        _parse.assert_called_once_with(self.new_repo_dir,
                                       upstream, codename='stable')

    def test_apt_repo_bad_signing_options(self):
        meta = AptRepoMeta(codename=self.name)
        with self.assertRaises(ValueError) as ctx:
            AptRepo(self.new_repo_dir, metadata=meta,
                    gpg_sign_options="really?")
        self.assertTrue(
            str(ctx.exception).startswith('gpg_sign_options: unexpected type'))
