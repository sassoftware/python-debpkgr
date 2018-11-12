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
import re

from six import string_types
from debian import deb822

from . import compressr
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
        default = codename.capitalize()
        self.release.setdefault('Description', description or default)
        origin = self.release.setdefault('Origin', origin or default)
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
        digests = ['SHA256', 'SHA1', 'MD5Sum']
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
                    path = os.path.join(re.sub(r'^.*/', '', comp), 'binary-{}'.format(arch))
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

    def release_dir(self, base_path):
        return os.path.join(
            base_path, 'dists', self.release['Codename'])

    def release_path(self, base_path):
        return os.path.join(
            self.release_dir(base_path), 'Release')

    def create(self, base_path):
        all_checksums = dict()
        for obj in self.iter_component_arch_binaries():
            checksums = obj.write_packages(
                base_path, self.release_dir(base_path))
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
    def WritePackages(cls, base_path, release_dir,
                      relative_path_fname, packages):
        """
        packages: iterator of objects with a dump() method (debpkg.DebPkg or
        deb822.Packages)
        """
        short_names = [relative_path_fname,
                       relative_path_fname + '.gz',
                       relative_path_fname + '.bz2',
                       ]
        pkg_files = [os.path.join(release_dir, x) for x in short_names]
        utils.makedirs(os.path.dirname(pkg_files[0]))

        pkg_plain, pkg_gz, pkg_bz2 = pkg_files
        try:
            # This will make sure the iterator will continue to work if one
            # exists, because it will point to a deleted file
            try:
                os.unlink(pkg_plain)
            except OSError as e:
                if e.errno != 2:
                    raise
            shutil.rmtree(pkg_plain, ignore_errors=True)
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
            src = os.path.join(release_dir, relative_fname)
            hashes = hash_file(src, algs=HA)
            size = str(os.stat(src).st_size)
            common = dict(name=relative_fname, size=size)
            for alg_name, (key_name, outer_name) in HA.items():
                info = dict(common)
                info[key_name] = hashes[alg_name]
                checksums.setdefault(outer_name, []).append(info)
        return short_names, checksums

    def create_Packages_download_requests(self, base_path):
        """
        Iterate over the release file and create a list of download request
        objects of type util.DownloadRequest
        """
        cmprsr = compressr.Opener()
        assert self.upstream_url is not None
        ca_to_flists = self.component_arch_binary_package_files_from_release()
        dl_reqs = []
        for (component, arch), flist in sorted(ca_to_flists.items()):
            path_to_fobj = dict((x['name'], x) for x in flist)
            preferred_filename = cmprsr.best_choice(path_to_fobj)[0]
            fobj = path_to_fobj[preferred_filename]
            caobj = self.get_component_arch_binary(component, arch)
            dl_meta = dict(fobj, component=component, architecture=arch)
            dest = os.path.join(base_path, caobj.relative_path('Packages'))
            # Remove trailing Packages, replace with the actual file name from
            # upstream
            dest = os.path.join(os.path.dirname(dest),
                                os.path.basename(preferred_filename))
            utils.makedirs(os.path.dirname(dest))
            dl_reqs.append(utils.DownloadRequest(
                os.path.join(self.upstream_url, preferred_filename),
                dest,
                dl_meta))

        return dl_reqs

    def validate_component_arch_packages_downloads(self, dl_reqs):
        """
        Validate the specified download requests, and, if successful,
        initialize the Packages object of the corresporning component_arch

        dl_reqs is a list of utils.DownloadRequest objects
        """
        cmprsr = compressr.Opener()
        # Validate downloads
        for dl in dl_reqs:
            algorithms = []
            for alg_name, (key_name, _) in self._Hash_Algorithms.items():
                if key_name in dl.data:
                    algorithms.append(alg_name)
                    break

            digests = hash_file(dl.destination, algorithms)
            if digests[alg_name] != dl.data[key_name]:
                raise Exception("Checksum did not match")

            component = dl.data['component']
            arch = dl.data['architecture']
            caobj = self.get_component_arch_binary(component, arch)
            ext = os.path.splitext(dl.destination)[1].lstrip('.')
            if ext in self._Compression_Types:
                dest = dl.destination[:-len(ext) - 1]
                shutil.copyfileobj(cmprsr.open(dl.destination, "rb"),
                                   open(dest, "wb"))
                os.unlink(dl.destination)
            else:
                dest = dl.destination
            caobj.packages_file = open(dest, "rb")
        return self


class ComponentArchBinary(object):
    __slots__ = ['release', '_packages', '_packages_file', 'dist']

    def __init__(self, release=None, packages=None, meta=None, dist=None):
        if release is None:
            release = deb822.Release()
        if meta is None:
            meta = dict()
        for k, v in meta.items():
            release.setdefault(k.capitalize(), v)
        self.release = release
        self._packages = packages
        self._packages_file = None
        self.dist = dist

    @property
    def component(self):
        return self.release['Component']

    @property
    def architecture(self):
        return self.release['Architecture']

    def add_package(self, pkg):
        if self._packages is None:
            self._packages = []
            self._packages_file = None
        self._packages.append(pkg)
        return self

    @property
    def packages_file(self):
        return self._packages_file

    @packages_file.setter
    def packages_file(self, value):
        self._packages_file = value
        self._packages_file.seek(0)

    def iter_packages(self):
        if self._packages is not None:
            return iter(self._packages)
        if self._packages_file is None:
            return iter([])
        self._packages_file.seek(0)
        return deb822.Packages.iter_paragraphs(self._packages_file)

    def load_packages(self, base_path):
        pkgs_relative_path = self.relative_path('Packages')
        self._packages_file = open(
            os.path.join(base_path, pkgs_relative_path))

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

    def write_packages(self, base_path, release_dir):
        pkgs_relative_path = os.path.join(
            self.component, 'binary-{}'.format(self.architecture), 'Packages')
        pkg_files, checksums = AptRepoMeta.WritePackages(
            base_path, release_dir, pkgs_relative_path, self.iter_packages())
        return checksums


class AptRepo(object):

    def __init__(self, path, metadata=None, gpg_sign_options=None,
                 repo_name=None):
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
        self._repo_name = repo_name

    @property
    def repo_name(self):
        if self._repo_name is not None:
            return self._repo_name
        return self.metadata.codename

    def _prefix(self, path):
        return os.path.join(self.base_path, path)

    def _prefixes(self, paths):
        return [self._prefix(path) for path in paths]

    @classmethod
    def make_download_request(cls, dl_request):
        """
        Convert a utils.DownloadRequest object into a download request object
        recognized by the download method.
        """
        return dl_request

    @classmethod
    def download(cls, requests):
        return utils.download(requests)

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
            component.add_package(pkg)

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
        req = cls.make_download_request(
            utils.DownloadRequest(release_file, dest, data=None))
        try:
            cls.download([req])
        except:  # noqa: E722
            log.error('Failed to open %s', release_file, exc_info=True)
            raise
        meta = AptRepoMeta(release=open(dest, "rb"), upstream_url=path)
        return cls(base_path, meta)

    @classmethod
    def parse(cls, base_path, path, codename=None):
        repoobj = cls.parse_release(base_path, path, codename=codename)
        meta = repoobj.metadata
        dl_reqs = meta.create_Packages_download_requests(base_path)
        repoobj.download([cls.make_download_request(x) for x in dl_reqs])
        meta.validate_component_arch_packages_downloads(dl_reqs)
        return repoobj


def create_repo(path, files, codename=None, components=None,
                arches=None, desc=None, origin=None, label=None,
                with_symlinks=False):
    if arches is not None:
        if isinstance(arches, string_types):
            arches = [x for x in arches.split() if x]
        if isinstance(components, string_types):
            components = [x for x in components.split() if x]
    metadata = AptRepoMeta(origin=origin,
                           label=label,
                           codename=codename,
                           components=components,
                           architectures=arches,
                           description=desc)
    repo = AptRepo(path, metadata=metadata)
    repo.create(files, with_symlinks=with_symlinks)
    return repo


def parse_repo(base_path, path, codename=None):
    repo = AptRepo.parse(base_path, path, codename=codename)
    return repo
