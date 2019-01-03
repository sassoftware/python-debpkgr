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
import subprocess

from debian import deb822
from debpkgr.aptrepo import AptRepo, AptRepoMeta
from debpkgr.aptrepo import create_repo
from debpkgr.aptrepo import parse_repo
from debpkgr.signer import SignOptions
from tests import base


class RepoTest(base.BaseTestCase):

    def setUp(self):
        super(RepoTest, self).setUp()
        self.repo_name = u'test_repo_foo'
        self.repo_codename = u'stable'
        self.repo_suite = u'suite'
        self.repo_component = u'main'
        self.repo_arches = u'i386 amd64'
        self.repo_description = u'Apt repository for Test Repo Foo'
        self.repo_bindirs = [u'dists/stable/main/binary-amd64',
                             u'dists/stable/main/binary-i386', ]

        self.repo_pools = [u'pool/main']
        self.repo_packages = {
            u'pool/main/f/foo/foo_0.0.1-1_amd64.deb': {
                'Package': u'foo',
                'Version': u'0.0.1-1',
                'Architecture': u'amd64',
                'Maintainer': u'Brett Smith <bc.smith@sas.com>',
                'Installed-Size': u'25',
                'Multi-Arch': u'foreign',
                'Homepage': u'https://github.com/xbcsmith/foo',
                'Priority': u'extra',
                'Section': u'database',
                'Filename': u'pool/main/f/foo/foo_0.0.1-1_amd64.deb',
                'Size': u'1464',
                'SHA256': u'd80568c932f54997713bb7832c6da6aa04992919f3d0f'
                            '47afb6ba600a7586780',
                'SHA1': u'5e26ae3ebf9f7176bb7fd01c9e802ac8e223cdcc',
                'MD5sum': u'5fc5c0cb24690e78d6c6a2e13753f1aa',
                'Description': u'So this is the Foo of Brixton program\n '
                'When they kick at your front door\n How you gonna come?\n '
                'With your hands on your head\n Or on the trigger of your gun'
            }
        }

        self.packagefile_paths = [u'main/binary-i386/Packages',
                                  u'main/binary-i386/Packages.gz',
                                  u'main/binary-i386/Packages.bz2',
                                  u'main/binary-amd64/Packages',
                                  u'main/binary-amd64/Packages.gz',
                                  u'main/binary-amd64/Packages.bz2']

    def test_create_repo(self):
        files = []
        for root, _, fl in os.walk(self.pool_dir):
            for f in fl:
                if f.endswith('.deb'):
                    files.append(os.path.join(root, f))

        repo = create_repo(self.new_repo_dir, files,
                           codename=self.repo_codename,
                           suite=self.repo_suite,
                           arches=self.repo_arches,
                           components=[self.repo_component],
                           desc=self.repo_description,
                           origin=self.repo_name)

        release_file = repo.metadata.release_path(repo.base_path)

        with open(release_file, 'r') as fh:
            release_data = fh.read()

        release_822 = deb822.Release(release_data)
        self.assertEqual(release_822.get('Origin'), self.repo_name)
        self.assertEqual(release_822.get('Label'), self.repo_name)
        self.assertEqual(
            release_822.get('Description'),
            self.repo_description)
        # Test handling of Architectures
        self.assertEqual(release_822.get('Architectures'), u'i386 amd64')
        self.assertEqual(repo.metadata.architectures, ['i386', 'amd64'])
        # Test package paths
        packagefile_paths_256 = [x['name'] for x in release_822['SHA256']]
        packagefile_paths_1 = [x['name'] for x in release_822['SHA1']]
        self.assertEqual(packagefile_paths_256, self.packagefile_paths)
        self.assertEqual(packagefile_paths_1, self.packagefile_paths)

    def test_AptRepo_create(self):
        test_dir = os.path.join(self.test_dir, self.repo_name, '_2001')

        packagefile_paths = [u'main/binary-amd64/Packages',
                             u'main/binary-amd64/Packages.gz',
                             u'main/binary-amd64/Packages.bz2']
        files = []
        for root, _, fl in os.walk(self.pool_dir):
            for f in fl:
                if f.endswith('.deb'):
                    files.append(os.path.join(root, f))
        arch = 'amd64'
        codename = 'stable'
        suite = 'suite'
        component = 'main'
        repometa = AptRepoMeta(
            codename=codename,
            suite=suite,
            components=[component],
            architectures=[arch])

        repo = AptRepo(test_dir,
                       repo_name=self.repo_name,
                       metadata=repometa,
                       gpg_sign_options=None)

        # Looking for bad behavior in defaults
        repo.create(files,
                    component=component,
                    architecture=arch,
                    with_symlinks=True)

        release_file = repo.metadata.release_path(repo.base_path)

        with open(release_file, 'r') as fh:
            release_data = fh.read()

        release_822 = deb822.Release(release_data)

        # Test defaults for Origin, Label, Description
        expected_default_origin = codename.capitalize()
        self.assertEqual(release_822.get('Origin'), expected_default_origin)
        self.assertEqual(release_822.get('Label'), expected_default_origin)
        self.assertEqual(
            release_822.get('Description'),
            expected_default_origin)
        # Test default for Suite
        self.assertEqual(release_822.get('Suite'), suite)
        # Test handling of Architectures
        self.assertEqual(release_822.get('Architectures'), arch)
        self.assertEqual(repo.metadata.architectures, [arch])
        packagefile_paths_256 = [x['name'] for x in release_822['SHA256']]
        packagefile_paths_1 = [x['name'] for x in release_822['SHA1']]
        self.assertEqual(packagefile_paths_256, packagefile_paths)
        self.assertEqual(packagefile_paths_1, packagefile_paths)

    def test_parse_repo(self):
        repo = parse_repo(self.new_repo_dir,
                          self.current_repo_dir, codename='stable')
        self.assertEqual(repo.repo_name, 'stable')
        self.assertEqual(repo.metadata.architectures, ['i386', 'amd64'])
        self.assertEqual(repo.metadata.release['label'], self.repo_name)
        self.assertEqual(repo.metadata.release['description'],
                         self.repo_description)

        comp_arch_bin = repo.metadata.get_component_arch_binary(
            'main', 'amd64')
        self.assertEqual(
            [self.repo_packages['pool/main/f/foo/foo_0.0.1-1_amd64.deb']],
            list(comp_arch_bin.iter_packages()))
        # Make sure we have a Packages file
        pkgs_file = os.path.join(self.new_repo_dir, 'dists', 'stable', 'main',
                                 'binary-amd64', 'Packages')
        self.assertTrue(os.path.exists(pkgs_file))
        stobj = os.stat(pkgs_file)
        sz = stobj.st_size
        inode = stobj.st_ino
        # Make sure we removed the .gz we have created
        self.assertFalse(os.path.exists(pkgs_file + '.gz'))
        # Make sure we can correctly write packages back
        comp_arch_bin.write_packages(self.new_repo_dir, repo.metadata.release_dir(
            self.new_repo_dir))

        self.assertEqual(sz - 1, os.stat(pkgs_file).st_size)
        self.assertNotEqual(inode, os.stat(pkgs_file).st_ino)

    # export REMOTE_TESTS=1 to activate
    @base.pytest.mark.skipif(os.environ.get('REMOTE_TESTS', '0') == '0',
                             reason='Remote Parse Test runs long')
    def test_parse_remote_repo(self):
        expected = u'Debian 3.1r8 Released 12th April 2008'
        url = "http://archive.debian.org/debian"
        repo = parse_repo(self.new_repo_dir, url, codename='sarge')
        desc = repo.metadata.release['Description']
        self.assertEqual(expected, desc)

    # export REMOTE_TESTS=1 to activate
    @base.pytest.mark.skipif(os.environ.get('REMOTE_TESTS', '0') == '0',
                             reason='Remote Parse Test runs long')
    def test_parse_release_remote_repo(self):
        expected = u'Debian 3.1r8 Released 12th April 2008'
        url = "http://archive.debian.org/debian"
        repo = AptRepo.parse_release(self.new_repo_dir, url, codename='sarge')
        desc = repo.metadata.release['Description']
        self.assertEqual(expected, desc)

    # export REMOTE_TESTS=1 to activate
    @base.pytest.mark.skipif(os.environ.get('REMOTE_TESTS', '0') == '0',
                             reason='Remote Parse Test runs long')
    def test_parse_remote_updates_repo(self):
        expected = u'Debian X Security Updates'
        url = "http://security.debian.org/debian-security"
        repo = parse_repo(self.new_repo_dir, url, codename='buster/updates')
        desc = repo.metadata.release['Description']
        self.assertEqual(expected, desc)

    # export REMOTE_TESTS=1 to activate
    @base.pytest.mark.skipif(os.environ.get('REMOTE_TESTS', '0') == '0',
                             reason='Remote Parse Test runs long')
    def test_parse_release_remote_updates_repo(self):
        expected = u'Debian X Security Updates'
        url = "http://security.debian.org/debian-security"
        repo = AptRepo.parse_release(self.new_repo_dir, url, codename='buster/updates')
        desc = repo.metadata.release['Description']
        self.assertEqual(expected, desc)

    def test_create_download_request_from_repo(self):
        repo = AptRepoMeta(
            release=open(os.path.join(self.current_repo_dir,
                                      'dists',
                                      'stable',
                                      'Release'), "rb"),
            upstream_url='file://%s' % self.current_repo_dir,
            codename='stable')
        self.assertNotEqual({}, repo.component_arch_binary_package_files_from_release())
        self.assertNotEqual([], repo.create_Packages_download_requests("/tmp"))

    def test_create_download_request_from_updates_repo(self):
        repo = AptRepoMeta(
            release=open(os.path.join(self.current_repo_dir,
                                      'dists',
                                      'updates',
                                      'stable',
                                      'Release'), "rb"),
            upstream_url='file://%s' % self.current_repo_dir,
            codename='updates/stable')
        self.assertNotEqual({}, repo.component_arch_binary_package_files_from_release())
        self.assertNotEqual([], repo.create_Packages_download_requests("/tmp"))

    def test__create_Packages_download_requests__md5(self):
        # PR #10: fix md5 in release-files
        # Tests that, in the absence of SHA1 and SHA256, MD5 will be used
        repo = AptRepoMeta(
            release=open(os.path.join(self.current_repo_dir,
                                      'dists',
                                      'stable',
                                      'Release'), "rb"),
            upstream_url='file://%s' % self.current_repo_dir,
            codename='stable')
        del repo.release['SHA1']
        del repo.release['SHA256']
        self.assertEqual(
            [('main', 'amd64'), ('main', 'i386')],
            sorted(repo.component_arch_binary_package_files_from_release().keys()))


class SignedRepoTest(base.BaseTestCase):

    def setUp(self):
        super(SignedRepoTest, self).setUp()
        self.gpg_home = os.path.join(self.test_dir, "gpg-home")
        os.makedirs(self.gpg_home, mode=0o700)
        self.gpg_base_cmd = ["gpg", "--homedir", self.gpg_home]
        self.gpg_key_id = "45BA0816"
        self._gpg_counter = 0

        self._run_gpg("--import",
                      os.path.join(self.current_repo_dir, "secret-keys.gpg"))

        gpg_signer_content = """\
#!/bin/bash -e

gpg --homedir %s \\
    --detach-sign --default-key $GPG_KEY_ID \\
    --armor --output ${1}.gpg ${1}
""" % (self.gpg_home, )
        self.gpg_signer = self.mkfile("gpgsign", contents=gpg_signer_content)
        os.chmod(self.gpg_signer, 0o755)

    def _run_gpg(self, *args):
        fobjs = []
        for f in "stdout", "stderr":
            fpath = os.path.join(self.test_dir,
                                 "gpg-%s-%d.log" % (f, self._gpg_counter))
            fobjs.append(open(fpath, "w+b"))

        cmd = self.gpg_base_cmd + list(args)
        ret = subprocess.call(cmd, stdout=fobjs[0], stderr=fobjs[1])
        for f in fobjs:
            f.close()

        if ret != 0:
            raise Exception("Command failed: retcode: %d; '%s'" %
                            (ret, ' '.join(cmd)))
        return fobjs[0].name, fobjs[1].name

    @base.mock.patch("debpkgr.aptrepo.debpkg.debfile")
    def test_sign(self, _debfile):
        file_names = ['foo_0.0.1-1_amd64.deb']
        files = [self.mkfile(x, contents=x) for x in file_names]

        D = deb822.Deb822
        # We need to reorder the files alphabetically, so the way os.walk
        # finds them is the same as the mock we're setting up
        Files = [
            (D(dict(Package="foo", Architecture="amd64", Version="0.0.1",
                    Release="1")), files[0])]
        pkgs = [x[0] for x in Files]
        debcontrol = _debfile.DebFile.return_value.control.debcontrol
        debcontrol.return_value.copy.side_effect = pkgs

        repo_name = "my-test-repo"

        defaults = dict(components=['main'],
                        architectures=['amd64'])
        gpg_sign_options = SignOptions(cmd=self.gpg_signer,
                                       key_id=self.gpg_key_id)
        meta = AptRepoMeta(codename=repo_name, **defaults)
        repo = AptRepo(self.new_repo_dir, meta,
                       gpg_sign_options=gpg_sign_options)
        repo.create([x[1] for x in Files], with_symlinks=True)
        relfile = os.path.join(self.new_repo_dir, 'dists', repo_name,
                               'Release')
        self.assertTrue(os.path.exists(relfile))
        relfile_signed = relfile + '.gpg'
        self.assertTrue(os.path.exists(relfile_signed))

        # Make sure the file verifies
        _, stderr = self._run_gpg("--verify", relfile_signed, relfile)
        # Make sure the file was signed with the proper key
        firstline = open(stderr, "rb").readline().strip()
        assert firstline.endswith(self.gpg_key_id.encode('utf-8'))

        # Check after the fact that gpg_sign_options was updated with a
        # repository_name and dist
        # We will rely on the functional test that the environment was
        # properly set up
        self.assertEqual(repo_name, gpg_sign_options.repository_name)
