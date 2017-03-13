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

import bz2
import gzip
import os
from collections import namedtuple

try:
    import lzma
except ImportError:
    from backports import lzma


Filename = namedtuple("Filename", "path base_name extension")
_Opener = namedtuple("_Opener", "factory extensions args_read args_write")


class Opener(object):
    _Decompressor_Factories = dict(
        gz=_Opener(gzip.open, extensions=['gz'], args_read=dict(),
                   args_write=dict(compresslevel=9)),
        xz=_Opener(lzma.LZMAFile, extensions=['xz'],
                   args_read=dict(), args_write=dict()),
        bz2=_Opener(bz2.BZ2File, extensions=['bz2', 'bzip2'],
                    args_read=dict(), args_write=dict()),
    )

    # Reverse lookup of decompressor by extension
    _Extension_to_decompressor = dict(
        bzip2='bz2',
        gz='gz',
        xz='xz',
        bz2='bz2')

    def __init__(self, preferences=None):
        if not preferences:
            preferences = ['xz', 'bz2', 'gz']
        else:
            preferences = [x for x in preferences
                           if x in self._Decompressor_Factories]
        self.preferences = preferences

    def best_choice(self, file_names):
        """
        Order file_names based on self.preferences
        This allows one to prefer an xz file over a gz
        """
        rank_dict = dict()
        for i, decompressor in enumerate(self.preferences):
            dobj = self._Decompressor_Factories[decompressor]
            for ext in dobj.extensions:
                rank_dict[ext] = i
        # No extension - least preferred
        rank_dict[None] = 1000

        objs = dict()
        for fname in file_names:
            f = self._File(fname)
            if f.extension not in rank_dict:
                continue
            objs.setdefault(f.base_name, set()).add(f)
        ret = []
        for _, objs in sorted(objs.items()):
            obj = min(objs, key=lambda x: rank_dict[x.extension])
            ret.append(obj.path)
        return ret

    def open(self, file_name, mode="rb", uncompressed=False):
        """
        If uncompressed is True, the file is opened in uncompressed mode,
        regardless of its extension.

        This is useful if the file has an extension already (like foo.xml) and
        we don't want to treat the extension as a compression indicator.
        """
        f = self._File(file_name)
        if uncompressed or f.extension is None:
            return open(file_name, mode)
        dname = self._Extension_to_decompressor.get(
            f.extension, f.extension)
        d = self._Decompressor_Factories.get(dname)
        if d is None:
            raise ValueError("Unsupported file %s" % file_name)
        if mode.startswith('r'):
            opts = d.args_read
        else:
            opts = d.args_write
        return d.factory(file_name, mode, **opts)

    @classmethod
    def _normalize_extension(cls, ext):
        if not ext:
            return None
        # Strip first dot
        return ext[1:]

    @classmethod
    def _File(cls, fpath):
        bname, ext = os.path.splitext(fpath)
        ext = cls._normalize_extension(ext)
        return Filename(fpath, bname, ext)


class MultiWriter(object):
    def __init__(self, fpath, extensions, opener=None):
        self.fpath = fpath
        if opener is None:
            opener = Opener()
        self.opener = opener
        supported_extensions = [
            x for x in extensions
            if x in opener._Extension_to_decompressor]
        self.file_names = ["{}.{}".format(fpath, ext)
                           for ext in supported_extensions]
        if None in extensions or '' in extensions:
            self.file_names.append(fpath)
        self.reset()

    def reset(self):
        self.file_objs = []
        for fname in self.file_names:
            uncompressed = (fname == self.fpath)
            self.file_objs.append(
                self.opener.open(fname, "wb", uncompressed=uncompressed))

    def write(self, block):
        for fobj in self.file_objs:
            fobj.write(block)

    def close(self):
        for fobj in self.file_objs:
            fobj.close()
        self.file_objs = []
