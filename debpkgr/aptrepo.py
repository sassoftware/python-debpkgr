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
from . import signer
from .hasher import hash_file

REPO_VERSION = '1.0'

log = logging.getLogger(__name__)


class AptRepoMeta(object):
    __slots__ = ['release', '_component_arch_binaries', 'upstream_url']
    """
    Object for storing Apt Repo MetaData
    """
    _Compression_Types = ['xz', 'bz2', 'gz']
    _Hash_Algorithms = dict(sha1=("sha1", "SHA1"),
                            md5=("md5sum", "MD5sum"),
                            sha256=("sha256", "SHA256"))

    def __init__(self, release=None, origin=None, label=None, version=None,
                 description=None, codename=None, components=None,
                 architectures=None, upstream_url=None):
        if release is None:
            release = deb822.Release()
        else:
            release = deb822.Release(release)
        if architectures is None:
            architectures = ['amd64', 'i386']
        if components is None:
            components = []
        self.release = release
        self.release.setdefault('Architectures', ' '.join(architectures))
        self.release.setdefault('Components', ' '.join(components))
        codename = self.release.setdefault('Codename', codename or 'foo')
        self.release.setdefault('Suite', codename)
        self.release.setdefault('Description', description or codename)
        origin = self.release.setdefault('Origin', origin or codename)
        self.release.setdefault('Label', label or origin)
        self.release.setdefault('Version', version or REPO_VERSION)
        self.set_date()
        self._component_arch_binaries = []
        self.upstream_url = upstream_url

    def set_date(self):
        self.release.setdefault(
            'Date', time.strftime('%a, %d %b %Y %H:%M:%S +0000',
                                  time.gmtime()))

    @property
    def architectures(self):
        return self.release.get('Architectures', '').split()

    @architectures.setter
    def architectures(self, values):
        assert isinstance(values, list)
        self.release['Architectures'] = ' '.join(values)

    @property
    def components(self):
        return self.release.get('Components', '').split()

    @property
    def codename(self):
        return self.release.get('Codename')

    @components.setter
    def _set_components(self, values):
        assert isinstance(values, list)
        self.release['Components'] = ' '.join(values)

    def init_component_arch_binaries(self):
        self._component_arch_binaries = []
        self._component_arch_binaries.extend(
            self.iter_component_arch_binaries())

    def iter_component_arch_binaries(self):
        for comp in self.components:
            for arch in self.architectures:
                yield self.get_component_arch_binary(comp, arch)

    def get_component_arch_binary(self, component, architecture):
        # Retrieves object, or creates it if it doesn't exist
        for obj in self._component_arch_binaries:
            if obj.component == component and obj.architecture == architecture:
                return obj
        return self.add_component_arch_binary(
            meta=dict(component=component, architecture=architecture))

    def component_arch_binary_package_files_from_release(self):
        digests = ['SHA256', 'SHA1', 'MD5']
        ret = dict()
        for digest_name in digests:
            if digest_name not in self.release:
                continue
            comp_arch_bin_packages = dict()
            for entry in self.release[digest_name]:
                dirname = os.path.dirname(entry['name'])
                comp_arch_bin_packages.setdefault(dirname, []).append(entry)
            for comp in self.components:
                for arch in self.architectures:
                    comparch = (comp, arch)
                    if comparch in ret:
                        continue
                    path = os.path.join(comp, 'binary-{}'.format(arch))
                    if path not in comp_arch_bin_packages:
                        continue
                    ret[comparch] = comp_arch_bin_packages[path]
        return ret

    def add_component_arch_binary(self, release=None, meta=None):
        if meta is not None:
            meta.setdefault('origin', self.release['Origin'])
            meta.setdefault('label', self.release['Label'])
            meta.setdefault('description', self.release['Description'])
        obj = ComponentArchBinary(release=release, meta=meta,
                                  dist=self.release['Codename'])
        if obj.component not in self.components:
            raise ValueError("Component %s not supported (expected: %s)" % (
                obj.component, ', '.join(self.components)))
        if obj.architecture not in self.architectures:
            raise ValueError("Architecture %s not defined (expected: %s)" % (
                obj.architecture, ', '.join(self.architectures)))
        self._component_arch_binaries.append(obj)
        return obj

    def release_path(self, base_path):
        return os.path.join(
            base_path, 'dists', self.release['Codename'], 'Release')

    def create(self, base_path):
        all_checksums = dict()
        for obj in self.iter_component_arch_binaries():
            checksums = obj.write_Packages(base_path)
            for k, vlist in checksums.items():
                all_checksums.setdefault(k, []).extend(vlist)
        self.release.update(all_checksums)
        self.write_release(base_path)

    def write_release(self, base_path):
        self.release.pop('Date', None)
        self.set_date()

        path = self.release_path(base_path)
        utils.makedirs(os.path.dirname(path))
        self.release.dump(open(path, "wb"))

    def dists_dir(self):
        return os.path.join(self.base_path, 'dists',
                            self.metadata.release['Codename'])

    @classmethod
    def Write_Packages(cls, base_path, relative_path_fname, packages):
        """
        packages: list of objects with a dump() method (debpkg.DebPkg or
        deb822.Packages)
        """
        short_names = [relative_path_fname,
                       relative_path_fname + '.gz',
                       relative_path_fname + '.bz2',
                       ]
        pkg_files = [os.path.join(base_path, x) for x in short_names]
        utils.makedirs(os.path.dirname(pkg_files[0]))

        pkg_plain, pkg_gz, pkg_bz2 = pkg_files
        try:
            with open(pkg_plain, 'wb') as pfh:
                first = True
                for pkg in packages:
                    if first:
                        first = False
                    else:
                        pfh.write(b"\n")
                    pkg.dump(pfh)
        except IOError:
            raise
        try:
            with open(pkg_plain, 'rb') as fhi:
                with gzip.open(pkg_gz, 'wb') as fhout:
                    shutil.copyfileobj(fhi, fhout)
                fhi.seek(0)
                with bz2.BZ2File(pkg_bz2, 'wb', compresslevel=9) as fhout:
                    shutil.copyfileobj(fhi, fhout)
        except IOError:
            raise

        HA = cls._Hash_Algorithms
        checksums = dict()
        for relative_fname in short_names:
            src = os.path.join(base_path, relative_fname)
            hashes = hash_file(src, algs=HA)
            size = str(os.stat(src).st_size)
            common = dict(name=relative_fname, size=size)
            for alg_name, (key_name, outer_name) in HA.items():
                info = dict(common)
                info[key_name] = hashes[alg_name]
                checksums.setdefault(outer_name, []).append(info)
        return short_names, checksums


class ComponentArchBinary(object):
    __slots__ = ['release', 'packages', 'dist']

    def __init__(self, release=None, packages=None, meta=None, dist=None):
        if release is None:
            release = deb822.Release()
        if meta is None:
            meta = dict()
        for k, v in meta.items():
            release.setdefault(k.capitalize(), v)
        self.release = release
        if packages is None:
            packages = []
        self.packages = packages
        self.dist = dist

    @property
    def component(self):
        return self.release['Component']

    @property
    def architecture(self):
        return self.release['Architecture']

    def load_packages(self, base_path):
        pkgs_relative_path = self.relative_path('Packages')
        return self._packages_from_file(
            os.path.join(base_path, pkgs_relative_path))

    def _packages_from_file(self, fobj):
        if not hasattr(fobj, 'read'):
            fobj = open(fobj, "rb")
        self.packages = list(deb822.Packages.iter_paragraphs(fobj))

    def relative_path(self, fname):
        return os.path.join(
            'dists', self.dist, self.release['Component'],
            'binary-{}'.format(self.release['Architecture']), fname)

    def release_path(self, base_path):
        return os.path.join(base_path, self.relative_path('Release'))

    @property
    def pool_relative_path(self):
        return os.path.join('pool', self.release['Component'])

    def pool_path(self, base_path):
        return os.path.join(base_path, self.pool_relative_path)

    def write_release(self, base_path):
        path = self.release_path(base_path)
        utils.makedirs(os.path.dirname(path))
        self.release.dump(open(path, "wb"))

    def write_Packages(self, base_path):
        pkgs_relative_path = self.relative_path('Packages')
        pkg_files, checksums = AptRepoMeta.Write_Packages(
            base_path, pkgs_relative_path, self.packages)
        return checksums


class AptRepo(object):

    def __init__(self, path, metadata=None, gpg_sign_options=None):
        self.base_path = path
        if gpg_sign_options is not None:
            if not isinstance(gpg_sign_options, signer.SignOptions):
                raise ValueError(
                    "gpg_sign_options: unexpected type %r" %
                    (gpg_sign_options, ))
        self.gpg_sign_options = gpg_sign_options
        if metadata is None:
            metadata = AptRepoMeta()
        self.metadata = metadata

    @property
    def repo_name(self):
        return self.metadata.codename

    def _prefix(self, path):
        return os.path.join(self.base_path, path)

    def _prefixes(self, paths):
        return [self._prefix(path) for path in paths]

    @classmethod
    def make_download_request(cls, url, destination, data=None):
        return utils.DownloadRequest(url, destination, data)

    @classmethod
    def download(cls, requests):
        return utils.download(requests)

    def _find_package_files(self, path):
        """
        Find all the Package* files in repo and
        and return a  hash dict
        """
        files = {}
        index = len(path.split(os.sep))
        for root, _, f in os.walk(path):
            for name in sorted(f):
                if name in self.metadata._filenames['packages']:
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

        self.sign(repo_release_file)

    def add_packages(self, filenames, component, architecture,
                     with_symlinks=False):
        component = self.metadata.get_component_arch_binary(
            component, architecture)
        dst_dir = component.pool_path(self.base_path)
        utils.makedirs(dst_dir)
        rel_path = component.pool_relative_path

        for filename in filenames:
            sz = str(os.stat(filename).st_size)
            pkg = debpkg.DebPkg.from_file(filename, Size=sz)
            dst_path = os.path.join(dst_dir, pkg.filename)
            pkg.relative_path = os.path.join(rel_path, pkg.filename)
            self._add_package(filename, dst_path, with_symlinks=with_symlinks)
            component.packages.append(pkg)

        return component

    def _add_package(self, filename, destination, with_symlinks=False):
        if with_symlinks:
            log.debug("Symlinking %s -> %s", filename, destination)
            if os.path.exists(destination):
                log.debug("    Removing existing destination")
                os.unlink(destination)
            os.symlink(filename, destination)
        else:
            log.debug("Copying %s -> %s", filename, destination)
            shutil.copy(filename, destination)

    def create(self, files=None, with_symlinks=False, component=None,
               architecture=None):
        # If component and architecture are not specified, default to the
        # first ones
        if files:
            if not component:
                component = self.metadata.components[0]
            if not architecture:
                architecture = self.metadata.architectures[0]
            self.add_packages(files, with_symlinks=with_symlinks,
                              component=component, architecture=architecture)
        self.metadata.create(self.base_path)
        self.sign(self.metadata.release_path(self.base_path))
        return

        dirs = []
        for d in self._prefixes(self.metadata.directories):
            dirs.append(utils.makedirs(d))
        if files:
            for pool in self._prefixes(self.metadata.pools):
                for f in files:
                    dst = os.path.join(pool, os.path.basename(f))
                    if with_symlinks:
                        log.debug("Using symlinks")
                        if os.path.exists(dst):
                            if os.path.islink(dst):
                                log.debug("Skipping link exists : %s" % dst)
                            else:
                                log.debug("Real file exists : %s" % dst)
                            continue
                        os.symlink(f, dst)
                    else:
                        log.debug("Copying file")
                        shutil.copy(f, dst)
        self.index()
        return

    def sign(self, release_file):
        if not self.gpg_sign_options:
            return
        self.gpg_sign_options.repository_name = self.repo_name
        _signer = signer.Signer(options=self.gpg_sign_options)
        return _signer.sign(release_file)

    @classmethod
    def parse_release(cls, base_path, path, codename=None):
        """
        Parse a repo from a path
        return AptRepo object
        """
        log.debug("Parsing %s" % path)
        if not path.endswith('Release'):
            if codename is not None and codename not in path:
                path = os.path.join(path, 'dists', codename)
        else:
            path = os.path.dirname(path)
        release_file = os.path.join(path, 'Release')
        # TODO Verify signatures
        # release_sig  = os.path.join(path, 'Release.gpg')
        dest = tempfile.NamedTemporaryFile(delete=False).name
        req = cls.make_download_request(release_file, dest)
        try:
            cls.download([req])
        except:
            log.error('Failed to open %s', release_file, exc_info=True)
            raise
        meta = AptRepoMeta(release=open(dest, "rb"), upstream_url=path)
        return cls(base_path, meta)

    @classmethod
    def parse_component_arch_binary_package_files(cls, meta):
        path = meta.upstream_url
        assert path is not None
        ca_to_flists = meta.component_arch_binary_package_files_from_release()
        dl_requests = []
        for (component, arch), flist in ca_to_flists.items():
            # XXX wire in compressr instead of grabbing the first
            fobj = flist[0]
            caobj = meta.get_component_arch_binary(component, arch)
            fname = fobj['name']
            dl_meta = dict(fobj, component=component, architecture=arch)
            dl_requests.append(
                cls.make_download_request(
                    os.path.join(path, fname),
                    tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix='-' + os.path.basename(fname)).name,
                    dl_meta))

        cls.download(dl_requests)
        # Validate downloads
        for dl in dl_requests:
            algorithms = []
            for alg_name, (key_name, _) in meta._Hash_Algorithms.items():
                if key_name in dl.data:
                    algorithms.append(alg_name)
                    break

            digests = hash_file(dl.destination, algorithms)
            if digests[alg_name] != dl.data[key_name]:
                raise Exception("Checksum did not match")

            component = dl.data['component']
            arch = dl.data['architecture']
            caobj = meta.get_component_arch_binary(component, arch)
            caobj._packages_from_file(dl.destination)
        return meta

    @classmethod
    def parse(cls, base_path, path, codename=None):
        repoobj = cls.parse_release(base_path, path, codename=codename)
        cls.parse_component_arch_binary_package_files(repoobj.metadata)
        return repoobj


def create_repo(path, files, name=None, components=None,
                arches=None, desc=None, with_symlinks=False):
    if arches is not None:
        if isinstance(arches, str):
            arches = [arches]
        if isinstance(components, str):
            components = [components]
    meta = AptRepoMeta(codename=name,
                       components=components,
                       architectures=arches,
                       description=desc)
    repo = AptRepo(path, meta)
    repo.create(files, with_symlinks=with_symlinks)
    return repo


def parse_repo(base_path, path, codename=None):
    repo = AptRepo.parse(base_path, path, codename=codename)
    return repo

# TODO


def index_repo(path, codename=None):
    raise NotImplementedError
