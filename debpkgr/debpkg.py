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
import inspect

from functools import total_ordering

log = logging.getLogger(__name__)

try:
    from debian import debfile
    from debian import deb822
    from debian.debian_support import Version
    from debian.debian_support import version_compare
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


class DebPkgRequires(object):

    __slots__ = ('depends', 'pre_depends', 'recommends',
                 'suggests', 'breaks', 'conflicts', 'provides', 'replaces',
                 'enhances')

    _defaults = dict((s, list()) for s in __slots__)

    def __init__(self, **kwargs):
        slots = self.__class__._all_slots()
        for k in slots:
            key = self._handle_key(k)
            if key in kwargs:
                val = self.parse(kwargs.get(key))
            else:
                val = self._defaults.get(k)
            setattr(self, k, val)

    def __repr__(self):
        return 'DebPkgRequires(%s)' % self.relations

    def _handle_key(self, k):
        if '_' in k:
            return '-'.join([x.capitalize() for x in k.split('_')])
        return k.capitalize()

    @classmethod
    def _all_slots(cls):
        slots = set()
        for kls in inspect.getmro(cls):
            slots.update(getattr(kls, '__slots__', []))
        return slots

    @property
    def relations(self):
        return dict((x, getattr(self, x)) for x in self._all_slots())

    @staticmethod
    def parse(raw):
        return deb822.PkgRelation.parse_relations(raw)

    def __str__(self):
        s = ""
        fmt = "%s : %s\n"
        for k in self._all_slots():
            key = self._handle_key(k)
            dep = getattr(self, k)
            if dep:
                s += fmt % (key, deb822.PkgRelation.str(dep))
        return s


class DebPkgScripts(object):

    __slots__ = ('preinst', 'postinst', 'prerm', 'postrm')

    _defaults = dict((s, None) for s in __slots__)

    def __init__(self, **kwargs):
        for k in self._defaults.keys():
            if k in kwargs:
                val = kwargs.get(k)
            else:
                val = self._defaults.get(k)
            setattr(self, k, val)

    def __repr__(self):
        return 'DebPkgScripts(%s)' % self

    @property
    def postinstall(self):
        return self.postinst

    @property
    def postremove(self):
        return self.postrm

    @property
    def preinstall(self):
        return self.preinst

    @property
    def preremove(self):
        return self.prerm


@total_ordering
class DebPkg(object):
    """Represent a binary debian package"""

    __slots__ = ("_c", "_h", "_md5", "_deps", "_version", "_scripts")

    def __init__(self, control, hashes, md5sums, scripts={}):
        if isinstance(control, dict):
            control = deb822.Deb822(control)
        self._c = control
        self._deps = DebPkgRequires(**self._c)
        self._version = Version(self._c.get('Version'))
        self._scripts = DebPkgScripts(**scripts)
        if isinstance(hashes, dict):
            hashes = deb822.Deb822(hashes)
        self._h = hashes
        if isinstance(md5sums, DebPkgMD5sums):
            self._md5 = md5sums
        else:
            self._md5 = DebPkgMD5sums(md5sums)

    def __repr__(self):
        return 'DebPkg(%s)' % self.nevra

    def __str__(self):
        return self.nevra

    def __hash__(self):
        return hash((self.name, self.version.full_version, self.arch))

    def __eq__(self, other):
        try:
            return self.__cmp__(other) == 0
        except (AttributeError, TypeError):
            return NotImplemented

    def __ne__(self, other):
        try:
            return not (self == other)
        except (AttributeError, TypeError):
            return NotImplemented

    def __lt__(self, other):
        try:
            return self.__cmp__(other) < 0
        except (AttributeError, TypeError):
            return NotImplemented

    def __cmp__(self, other):
        if self is other:
            return 0
        if self.version == other.version:
            if (self._c, self._h, self._md5) == (
                    other._c, other._h, other._md5):
                return 0
            return -1
        else:
            return version_compare(
                self.version.full_version, other.full_version)

    @property
    def package(self):
        package = self._c.copy()
        package.update(self._h)
        return package

    @property
    def files(self):
        return DebPkgFiles([x for x in self._md5.keys()])

    @property
    def scripts(self):
        return self._scripts

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
    def filename(self):
        return self.nevra + '.deb'

    @property
    def relative_path(self):
        return self._c.get('Filename')

    @relative_path.setter
    def relative_path(self, value):
        self._c['Filename'] = value

    @property
    def name(self):
        return self._c['Package']

    @property
    def epoch(self):
        return self._version.epoch or '0'

    @property
    def full_version(self):
        return self._version.full_version

    @property
    def upstream_version(self):
        return self._version.upstream_version

    @property
    def debian_version(self):
        return self._version.debian_version

    @property
    def debian_revision(self):
        return self._version.debian_revision

    @property
    def version(self):
        return self._version

    @property
    def arch(self):
        return self._c['Architecture']

    @property
    def nevra(self):
        return '_'.join([self.name, self._version.full_version, self.arch])

    @property
    def depends(self):
        return self._deps.depends

    @property
    def dependencies(self):
        return self._deps.relations

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
        # existance of md5sums in control part is optional
        try:
            md5sums = debpkg.md5sums(encoding='utf-8')
        except debfile.DebError as err:
            log.warn('While processing %s: %s', path, err.args[0])
            md5sums = None
        control = debpkg.control.debcontrol().copy()
        scripts = debpkg.control.scripts()
        hashes = cls.make_hashes(path)
        control.update(kwargs)
        return cls(control, hashes, md5sums, scripts=scripts)

    def dump(self, path):
        return self.package.dump(path)
