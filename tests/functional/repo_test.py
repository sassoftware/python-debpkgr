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
from debpkgr.aptrepo import AptRepo, SignOptions
from debpkgr.aptrepo import create_repo
from debpkgr.aptrepo import parse_repo
from debpkgr.aptrepo import index_repo
from tests import base


class RepoTest(base.BaseTestCase):

    def test_create_repo(self):
        name = 'test_repo_foo'  # should match Origin and Label
        arches = ['amd64', 'i386']
        description = 'Apt repository for Test Repo Foo'
        files = []
        for root, _, fl in os.walk(self.pool_dir):
            for f in fl:
                if f.endswith('.deb'):
                    files.append(os.path.join(root, f))

        repo = create_repo(self.new_repo_dir, files, name=name,
                           arches=arches, desc=description)

        repo_dir = os.path.join(self.new_repo_dir, repo.metadata.repodir)
        release_file = os.path.join(repo_dir, 'Release')

        with open(release_file, 'r') as fh:
            release_data = fh.read()

        release_822 = deb822.Release(release_data)

        self.assertEquals(release_822.get('Origin'), name)
        self.assertEquals(release_822.get('Label'), name)
        self.assertEquals(release_822.get('Description'), description)

        new_files = [os.path.basename(x)
                     for x in repo.metadata.archives.keys()]
        orig_files = [os.path.basename(x) for x in files]

        self.assertEquals(new_files, orig_files)

        # assert release_data == False

    def X_test_index_repo(self):
        repo = index_repo(self.new_repo_dir)
        print(repo.name)

    def X_test_parse_repo(self):
        repo = parse_repo(self.current_repo_dir)
        print(repo.name)


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
        repo = AptRepo(self.new_repo_dir, repo_name,
                       gpg_sign_options=gpg_sign_options, **defaults)
        repo.create([x[1] for x in Files], with_symlinks=True)
        relfile = os.path.join(self.new_repo_dir, 'dists', 'stable',
                               'Release')
        self.assertTrue(os.path.exists(relfile))
        relfile_signed = relfile + '.gpg'
        self.assertTrue(os.path.exists(relfile_signed))

        # Make sure the file verifies
        _, stderr = self._run_gpg("--verify", relfile_signed, relfile)
        # Make sure the file was signed with the proper key
        firstline = open(stderr, "rb").readline().strip()
        assert firstline.endswith(self.gpg_key_id.encode('utf-8'))
