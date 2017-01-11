#!/usr/bin/env python

'''
Python implementation to create an apt repo from a pile of .deb

If it fails you get to keep the pieces

pip install python-debian chardet

'''

import os
import shutil
import time
import gzip
import bz2
import tempfile

from collections import namedtuple

from debian import deb822

import debpkg
import utils
from hasher import hash_file

REPO_VERSION = '1.0'


class AptRepoMeta(namedtuple('AptRepoMeta', 'codename origin label version description architectures components')):

    """
    Object for storing Apt Repo MetaData
    """


class AptRepo(object):

    def __init__(self, name=None, codename=None, components=None, arches=None, description=None):
        self.origin = name or 'foo_test_repo'
        self.label = name or 'foo_test_repo'
        self.version = REPO_VERSION
        self.description = description or 'Foo Test Repo'
        self.codename = codename or 'stable'
        self.components = components or [ 'main' ]
        self.repodir = os.path.join('dists', self.codename)
        self.arches = arches or ['amd64']
        self.pools = [ os.path.join('pool', x) for x in self.components ]
        self.bindirs = []
        for arch in self.arches:
            for component in self.components:
                self.bindirs.append(
                    os.path.join(component, 'binary-{0}'.format(arch)))

        self.metadata = AptRepoMeta(
            self.codename, self.origin, self.label, self.version, 
            self.description, self.arches, self.components)

        self.archives = {}
        self.skeleton_dirs = [os.path.join(self.repodir, x)
                              for x in self.bindirs] + self.pools

    def _find_package_files(self, path):
        """
        Find all the Package* files in repo and
        and return a  hash dict
        """
        files = {}
        index = len(path.split(os.sep))
        for root, _, f in os.walk(path):
            for name in f:
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
        return files

    def _find_archive_files(self, path):
        files = {}
        for root, _, f in os.walk(path):
            for name in f:
                if name.endswith('.deb'):
                    fp = os.path.join(root, name)
                    pkg = debpkg.DebPkg.from_file(fp)
                    self.archives.setdefault(fp, pkg)
        return files

    def parse(self, path):
        pass

    def create(self, files, symlinks=False):
        dirs = []
        for d in self.skeleton_dirs:
            dirs.append(utils.makedirs(d))
        if files:
            for pool in self.pools:
                for f in files:
                    if symlinks:
                        # TODO Make symlinks
                        print("Using symlinks")
                    else:
                        print("Copying file")
                        shutil.copy(f, pool)
        index = self.index()
        return index

    def index(self):
        print("Indexing %s" % self.codename)
        bindirs = []

        for pool in self.pools:
            self._find_archive_files(pool)

        for root, dirs, _ in os.walk(self.repodir):
            for x in dirs:
                if x.startswith('binary'):
                    bindirs.append(os.path.join(root, x))

        for path in bindirs:
            bindir = os.path.basename(path)
            arch = bindir.split('-')[-1]
            component = path.split(os.sep)[-2]
            print("Architecture : %s" % arch)
            if arch not in self.arches:
                continue
            print("Processing {0} with arch {1}".format(bindir, arch))

            # FIXME use mktemp
            overrides_file = tempfile.TemporaryFile(prefix="overrides")
            overrides_content = ""
            packages_content = ""

            package_file = os.path.join(path, 'Packages')
            package_file_gz = os.path.join(path, 'Packages.gz')
            package_file_bz2 = os.path.join(path, 'Packages.bz2')
            release_file = os.path.join(path, 'Release')
            release_content = deb822.Release({ 'Component': component,
                                            'Origin': self.origin,
                                            'Label': self.label,
                                            'Description': self.description,
                                            'Architecture': arch,
                                    })

            for name, pkg in self.archives.items():
                overrides_content += "%s Priority extra\n" % pkg.name
                packages_content += str(pkg.package) + "\n"

            overrides_file.write(overrides_content)

            with open(package_file, 'w') as pfh:
                pfh.write(packages_content)

            with open(package_file, 'rb') as fhi, gzip.open(package_file_gz, 'wb') as fhgz, bz2.BZ2File(package_file_bz2, 'wb', compresslevel=9) as fhbz:
                shutil.copyfileobj(fhi, fhgz)
                fhi.seek(0)
                shutil.copyfileobj(fhi, fhbz)

            with open(release_file, 'w') as fhr:
                fhr.write(str(release_content))

            # Cleanup overrides file is silly
            overrides_file.close()

        # Make Main Release
        pack = self._find_package_files(self.repodir)
        package_md5sums = '\n'.join(
            [' '.join(x['md5sum']) for x in pack.values()])
        package_sha1sums = '\n'.join(
            [' '.join(x['sha1']) for x in pack.values()])
        package_sha256sums = '\n'.join(
            [' '.join(x['sha256']) for x in pack.values()])
        repo_release_file = os.path.join(self.repodir, 'Release')
        repo_release_content = deb822.Release({'Codename': self.codename,
                                         'Version': self.version,
                                         'Components': ' '.join(self.components),
                                         'Origin': self.origin,
                                         'Label': self.label,
                                         'Description': self.description,
                                         'Architectures': ' '.join(self.arches),
                                         'Date': time.strftime('%a %b %T %Z %Y'),
                                         'MD5Sum': package_md5sums,
                                         'SHA1': package_sha1sums,
                                         'SHA256': package_sha256sums,
                                          })

        with open(repo_release_file, 'w') as fhr:
            fhr.write(str(repo_release_content))

        # FIXME Sign the Release file

        return release_content

    def sign(self):
        raise NotImplementedError

def create_repo(files, name=None, arch=None, desc=None):
    repo = AptRepo(name=name, arches=[arch], description=desc)
    repo.create(files)
    import epdb;epdb.st()
        

if __name__ == '__main__' :
    import sys
    create_repo(sys.argv[1:])
