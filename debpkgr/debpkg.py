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


'''
Python implementation to extract info from .deb

If it fails you get to keep the pieces

pip install python-debian chardet

'''

from __future__ import absolute_import
from __future__ import division
from __future__ import unicode_literals

import logging
import sys

log = logging.getLogger(__name__)

try:
    from debian import debfile
    from debian import deb822
except Exception:
    log.error(
        "[ERROR] Failed to import debian\n"
        "pip install python-debian chardet\n")
    sys.exit()

try:
    # Can't check version so need to support xz
    assert 'xz' in debfile.PART_EXTS
except Exception:
    log.error(
        "[ERROR] python-debian missing xz support\n"
        "pip install --upgrade python-debian chardet\n")
    sys.exit()


from .hasher import deb_hash_file

from six.moves import UserList


class DebPkgFiles(UserList):

    def __init__(self, *args, **kwargs):
        super(DebPkgFiles, self).__init__(*args, **kwargs)

    def __repr__(self):
        return 'DebPkgFiles(%s)' % sorted(self.data)

    def __str__(self):
        return "\n".join(sorted(self.data))

    def __eq__(self, other):
        if isinstance(other, self.__class__):
            return sorted(self.__dict__) == sorted(other.__dict__)
        elif isinstance(other, (list, tuple)):
            return self.data == other
        return False

    def __ne__(self, other):
        if isinstance(other, self.__class__):
            return not self.__eq__(other)
        return not self == other


class DebPkgMD5sums(deb822.Deb822):

    def __repr__(self):
        return 'DebPkgMD5sums(%s)' % self

    def __str__(self):
        results = u""
        keys = sorted([x for x in self.keys()])
        for k in keys:
            results += u"{0} {1}\n".format(k, self.get(k))
        # for k, v in self.items():
        #    results += u"%s %s\n" % (k, v)
        return results


class DebPkg(object):
    __slots__ = ("_c", "_h", "_md5")

    def __init__(self, control, hashes, md5sums):
        if isinstance(control, dict):
            control = deb822.Deb822(control)
        self._c = control
        if isinstance(hashes, dict):
            hashes = deb822.Deb822(hashes)
        self._h = hashes
        if isinstance(md5sums, DebPkgMD5sums):
            self._md5 = md5sums
        else:
            self._md5 = DebPkgMD5sums(md5sums)

    def __repr__(self):
        return 'DebPkg(%s)' % self.nvra

    def __str__(self):
        return self.nvra

    @property
    def package(self):
        package = self._c.copy()
        package.update(self._h)
        return package

    @property
    def files(self):
        return DebPkgFiles([x for x in self._md5.keys()])

    @property
    def md5sums(self):
        return self._md5

    @property
    def hashes(self):
        return self._h

    @property
    def control(self):
        return self._c

    @property
    def nvra(self):
        return '_'.join([self._c['Package'], self._c['Version'],
                         self._c['Architecture']])

    @property
    def filename(self):
        return self.nvra + '.deb'

    @property
    def name(self):
        return self._c['Package']

    @property
    def version(self):
        return self._c['Version'].split('-')[0]

    @property
    def release(self):
        return self._c['Version'].split('-')[-1] or None

    @property
    def arch(self):
        return self._c['Architecture']

    @property
    def md5sum(self):
        return self._h['MD5sum']

    @property
    def sha1(self):
        return self._h['SHA1']

    @property
    def sha256(self):
        return self._h['SHA256']

    @staticmethod
    def make_hashes(path):
        return deb_hash_file(path)

    @classmethod
    def from_file(cls, path, **kwargs):
        """
        Allows for fields (like Filename and Size) to be added or replaced
        using keyword arguments.
        """
        debpkg = debfile.DebFile(filename=path)
        md5sums = debpkg.md5sums(encoding='utf-8')
        control = debpkg.control.debcontrol().copy()
        hashes = cls.make_hashes(path)
        control.update(kwargs)
        return cls(control, hashes, md5sums)
