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

import os

from debpkgr import compressr

from tests import base


class DecompressorTest(base.BaseTestCase):
    def test_preferences(self):
        dobj = compressr.Opener()
        self.assertEqual(["xz", "bz2", "gz"], dobj.preferences)

        prefs = ["bz2", "gz"]
        dobj = compressr.Opener(preferences=prefs)
        self.assertEqual(prefs, dobj.preferences)

    def test_rank(self):
        dobj = compressr.Opener()

        fnames = ["path1/Packages.gz", "path3/Packages.bz2",
                  "path1/Packages.xz",
                  "path1/Packages.leave-me-alone",
                  "path1/Packages",
                  "path2/Packages"]
        ret = dobj.best_choice(fnames)
        self.assertEqual(
            ['path1/Packages.xz', 'path2/Packages', 'path3/Packages.bz2'],
            ret)

    def _test_open(self, fname_uncompressed, with_uncompressed=True):
        dobj = compressr.Opener()
        file_names = [fname_uncompressed]
        for ext in ['bzip2', 'xz', 'bz2', 'gz']:
            fname = "foo.{}".format(ext)
            file_names.append(fname)
        # We don't want to explicitly test the writer at this point, but might
        # as well
        for fname in file_names:
            if with_uncompressed:
                kwargs = dict(uncompressed=(fname == fname_uncompressed))
            else:
                kwargs = {}
            fobj = dobj.open(fname, "wb", **kwargs)
            fobj.write(b"Test" * 100)
            fobj.close()
            fsize = os.stat(fname).st_size
            if fname == fname_uncompressed:
                self.assertEqual(400, fsize)
            else:
                self.assertTrue(fsize < 400)
        for fname in file_names:
            if with_uncompressed:
                kwargs = dict(uncompressed=(fname == fname_uncompressed))
            else:
                kwargs = {}
            fobj = dobj.open(fname, **kwargs)
            self.assertEqual(b"Test" * 100, fobj.read())

    def test_open_no_extension(self):
        fname_uncompressed = "foo"
        self._test_open(fname_uncompressed, with_uncompressed=False)
        self._test_open(fname_uncompressed, with_uncompressed=True)

    def test_open_with_extension(self):
        fname_uncompressed = "foo.txt"
        self._test_open(fname_uncompressed, with_uncompressed=True)

    def test_multi_writer(self):
        obj = compressr.MultiWriter(
            os.path.join(self.test_dir, "foo"),
            extensions=['bzip2', 'xz', 'bz2', 'gz', None])
        for i in range(100):
            obj.write(b"Test")
        obj.close()

    def test_maps(self):
        # Make sure that all the maps are sane
        _Algs = compressr.Opener._Decompressor_Factories
        extensions = compressr.Opener._Extension_to_decompressor
        for alg_name, factory in _Algs.items():
            for ext in factory.extensions:
                assert ext in extensions
        for ext, alg_name in extensions.items():
            assert alg_name in _Algs
