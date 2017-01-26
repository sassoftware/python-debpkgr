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
Python implementation to create an apt repo from a pile of .deb

If it fails you get to keep the pieces

pip install python-debian chardet

'''

from __future__ import absolute_import
from __future__ import unicode_literals

import inspect
import logging
import os
import shutil
import time
import gzip
import bz2
import tempfile

from debian import deb822

from . import debpkg
from . import utils
from .hasher import hash_file

REPO_VERSION = '1.0'

log = logging.getLogger(__name__)


class BaseModel(object):
    __slots__ = []
    _defaults = {}

    def __init__(self, **kwargs):
        slots = self.__class__._all_slots()
        for k in slots:
            if k in kwargs:
                setattr(self, k, kwargs.get(k))
            else:
                setattr(self, k, self._defaults.get(k))

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        slots = set()
        for kls in inspect.getmro(self.__class__):
            slots.update(getattr(kls, '__slots__', []))
        for k in slots:
            if getattr(self, k) != getattr(other, k):
                return False
        return True

    def __repr__(self):
        rdata = sorted(self.as_dict().items())
        return "<%s object at 0x%x; %s>" % (
            self.__class__, id(self),
            ", ".join("%s=%r" % (k, v) for (k, v) in rdata))

    __str__ = __repr__

    @classmethod
    def _all_slots(cls):
        slots = set()
        for kls in inspect.getmro(cls):
            slots.update(getattr(kls, '__slots__', []))
        return slots

    def as_dict(self, blacklist_fields=None):
        if blacklist_fields is None:
            blacklist_fields = set()
        slots = set()
        for kls in inspect.getmro(self.__class__):
            slots.update(getattr(kls, '__slots__', []))
        rdata = {}
        for k in slots:
            if k in blacklist_fields:
                continue
            v = getattr(self, k)
            if v is not None:
                rdata[k] = v
        return rdata


class AptRepoMeta(BaseModel):

    """
    Object for storing Apt Repo MetaData
    """

    _defaults = {'origin': 'foo',
                 'label': 'foo',
                 'version': REPO_VERSION,
                 'description': 'Foo Description',
                 'codename': 'stable',
                 'components': ['main'],
                 'architectures': ['amd64', 'i386'],
                 'archives': {},  # path : deb822 pkg
                 'packages': {},
                 'releases': {},
                 }

    __slots__ = tuple(_defaults.keys())

    @property
    def repodir(self):
        return os.path.join('dists', self.codename)

    @property
    def pools(self):
        return [os.path.join('pool', x) for x in self.components]

    @property
    def bindirs(self):
        dirs = []
        for arch in self.architectures:
            for component in self.components:
                dirs.append(os.path.join(self.repodir, component,
                                         'binary-{0}'.format(arch)))
        return dirs

    @property
    def directories(self):
        return self.bindirs + self.pools

    def make_release(self, component, arch):
        content = {'Component': component,
                   'Origin': self.origin,
                   'Label': self.label,
                   'Description': self.description,
                   'Architecture': arch,
                   }

        return deb822.Release(content)

    def make_repo_release(self, hashdict=None):

        content = {'Suite': self.codename,
                   'Codename': self.codename,
                   'Version': self.version,
                   'Components': ' '.join(self.components),
                   'Origin': self.origin,
                   'Label': self.label,
                   'Description': self.description,
                   'Architectures': ' '.join(self.architectures),
                   'Date': time.strftime('%a %b %T %Z %Y'),
                   }

        if hashdict:
            md5sums = '\n'.join(
                [' '.join(x['md5sum']) for x in hashdict])
            sha1sums = '\n'.join(
                [' '.join(x['sha1']) for x in hashdict])
            sha256sums = '\n'.join(
                [' '.join(x['sha256']) for x in hashdict])
            content.update({'MD5Sum': md5sums,
                            'SHA1': sha1sums,
                            'SHA256': sha256sums,
                            })

        return deb822.Release(content)


class AptRepo(object):

    def __init__(self, path, name, **kwargs):
        self.base_path = path
        self.repo_name = name
        metadata = dict(origin=name, label=name)
        for k, v in kwargs.items():
            if k in AptRepoMeta._all_slots() and v is not None:
                metadata.setdefault(k, v)
        self.metadata = AptRepoMeta(**metadata)

    def _prefix(self, path):
        return os.path.join(self.base_path, path)

    def _prefixes(self, paths):
        return [self._prefix(path) for path in paths]

    def _find_package_files(self, path):
        """
        Find all the Package* files in repo and
        and return a  hash dict
        """
        files = {}
        index = len(path.split(os.sep))
        for root, _, f in os.walk(path):
            for name in sorted(f):
                if name.startswith('Package'):
                    full_path = os.path.join(root, name)
                    short_path = os.sep.join(full_path.split(os.sep)[index:])
                    algs = ["md5", "sha1", "sha256"]
                    hashes = hash_file(os.path.abspath(full_path), algs=algs)
                    size = str(os.stat(full_path).st_size)
                    info = {
                        "md5sum": [hashes["md5"], size, short_path],
                        "sha1": [hashes["sha1"], size, short_path],
                        "sha256": [hashes["sha256"], size, short_path],
                    }
                    files.setdefault(short_path, info)
        self.metadata.packages = files
        return files

    def _find_archive_files(self, relpath):
        path = self._prefix(relpath)
        # Collect the lead (usually self.base_path)
        lead = path[:-len(relpath)].rstrip(os.sep)
        # Skip over trailing backslash
        lead_len = len(lead) + 1
        files = {}
        for root, _, f in os.walk(path):
            for name in sorted(f):
                if name.endswith('.deb'):
                    fp = os.path.join(root, name)
                    Filename = fp[lead_len:]
                    sz = str(os.stat(fp).st_size)
                    pkg = debpkg.DebPkg.from_file(fp, Filename=Filename,
                                                  Size=sz)
                    self.metadata.archives.setdefault(fp, pkg)
        return files

    def _create_overrides(self):
        overrides_file = tempfile.TemporaryFile(prefix="overrides")
        overrides_content = ""
        for name, pkg in self.archives.items():
            overrides_content += "%s Priority extra\n" % pkg.name
        overrides_file.write(overrides_content)
        return overrides_file

    def _write_packages_files(self, path, packages):
        package_file = os.path.join(path, 'Packages')
        package_file_gz = os.path.join(path, 'Packages.gz')
        package_file_bz2 = os.path.join(path, 'Packages.bz2')
        try:
            with open(package_file, 'wb') as pfh:
                for pkg in packages:
                    pkg.dump(pfh)
                    pfh.write(b"\n")
        except IOError as err:
            raise err.args[0]
        try:
            with open(package_file, 'rb') as fhi:
                with gzip.open(package_file_gz, 'wb') as fhgz:
                    shutil.copyfileobj(fhi, fhgz)
                fhi.seek(0)
                with bz2.BZ2File(package_file_bz2,
                                 'wb', compresslevel=9) as fhbz:
                    shutil.copyfileobj(fhi, fhbz)
        except IOError as err:
            raise err.args[0]

    def index(self):
        log.debug("Indexing %s", self.metadata.codename)

        for pool in self.metadata.pools:
            file_list = self._find_archive_files(pool)
            log.debug("Processing Archives:")
            for f in file_list:
                log.debug(f)

        for path in self._prefixes(self.metadata.bindirs):
            bindir = os.path.basename(path)
            arch = bindir.partition('-')[-1]
            component = path.split(os.sep)[-2]
            log.debug("Processing {0} with arch {1}".format(bindir, arch))
            packages_content = []
            for name, pkg in sorted(self.metadata.archives.items()):
                if pkg.arch == arch:
                    packages_content.append(pkg.package)

            self._write_packages_files(path, packages_content)

            release_file = os.path.join(path, 'Release')
            release_content = self.metadata.make_release(component, arch)

            with open(release_file, 'w') as fhr:
                fhr.write(str(release_content))

            self.metadata.releases.setdefault(release_file, release_content)

        # Make Main Release
        self.metadata.packages = self._find_package_files(
            self._prefix(self.metadata.repodir))
        repo_release_file = self._prefix(os.path.join(self.metadata.repodir,
                                                      'Release'))
        repo_release_content = self.metadata.make_repo_release(
            hashdict=self.metadata.packages.values())

        with open(repo_release_file, 'w') as fhr:
            fhr.write(str(repo_release_content))

        self.metadata.releases.setdefault(repo_release_file,
                                          repo_release_content)

        # FIXME Sign the Release file

    def create(self, files, with_symlinks=False):
        dirs = []
        for d in self._prefixes(self.metadata.directories):
            dirs.append(utils.makedirs(d))
        if files:
            for pool in self._prefixes(self.metadata.pools):
                for f in files:
                    dst = os.path.join(pool, os.path.basename(f))
                    if with_symlinks:
                        log.debug("Using symlinks")
                        os.symlink(f, dst)
                    else:
                        log.debug("Copying file")
                        shutil.copy(f, dst)
        self.index()
        return

    def sign(self):
        raise NotImplementedError

    @classmethod
    def parse(cls, path):
        """
        Parse a repo from a path
        return AptRepo object
        """
        pass


def create_repo(path, files, name=None, arches=None, desc=None):
    if arches is not None:
        if isinstance(arches, str):
            arches = [arches]
    repo = AptRepo(path, name, architectures=arches,
                   description=desc)
    repo.create(files)
    return repo


def index_repo(path):
    repo = AptRepo.parse(path)
    repo.index()
    return repo


def parse_repo(path):
    repo = AptRepo.parse(path)
    return repo
