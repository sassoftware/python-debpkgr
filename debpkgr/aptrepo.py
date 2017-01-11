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

from debian import deb822

from . import debpkg
from . import utils
from hasher import hash_file

def AptRepo(object):

    def __init__(self, reponame=None, arches=None, pool=None):
        self.reponame = reponame or 'stable'
        self.repodir = os.path.join('dists', self.reponame)
        self.arches = arches or [ 'amd64' ]   
        self.pool = pool or 'pool/main'
        self.bindirs = []
        for arch in self.arches:
            # FIXME think "main" should be basename self.pool... not sure
            self.bindirs.append(os.path.join('main', 'binary-{0}'.format(self.arch)))
        self.packages = {}
        self.skeleton_dirs = [ os.path.join(self.repodir, x) for x in self.bindirs ] + [ self.pool ]  


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
                    full_path = os.path.join(root,name)
                    short_path = os.sep.join(full_path.split(os.sep)[index:])
                    algs = [ "md5", "sha1", "sha256" ]
                    hashes = hash_file(os.path.abspath(full_path), algs=algs)
                    size = str(os.stat(full_path).st_size)

                    info = { 
                        "md5sum": [ hashes["md5"], size, short_path ],
                        "sha1": [ hashes["sha1"], size, short_path ],
                        "sha256": [ hashes["sha256"], size, short_path ],
                    }
                    files.setdefault(short_path, info)
        return files


    def parse(self, path):
        pass

    def create(self, files, symlinks=False):            
        dirs = []
        for d in self.skeleton_dirs:
            dirs.append(utils.makedirs(d))
        if files:
            for f in files:
                if symlinks:
                    # TODO Make symlinks
                    print("Using symlinks")
                else:
                    print("Copying file")
                    shutil.copy(f, self.pool)
        index = self.index()
        return index

    def index(self):
        print("Indexing %s" % self._reponame) 
        pool_files = [os.path.join(self.pool, x)
                  for x in os.listdir(self.pool) if x.endswith('.deb')]

        for path in pool_files:
            pkg = debpkg.DebPkg.from_file(path)
            self.packages.setdefault(pkg.name, pkg)

        bindirs = []
        for root, dirs, _ in os.walk(self._repodir): 
            for x in dirs: 
                if x.startswith('binary'):
                    bindirs.append(os.path.join(root, x))

        for path in bindirs:
            bindir = os.path.basename(path)
            arch = bindir.split('-')[-1]
            print("Architecture : %s" % arch)
            if arch != switches['arch']:
                continue
            print("Processing {0} with arch {1}".format(bindir, arch))

            # FIXME use mktemp
            overrides_file = "/tmp/overrides"
            overrides_content = ""
            packages_content = ""
 
            package_file = os.path.join(path, 'Packages')
            package_file_gz = os.path.join(path, 'Packages.gz')
            package_file_bz2 = os.path.join(path, 'Packages.bz2')
            
            for name, pkg in packages.items():
                overrides_content += "%s Priority extra\n" % pkg.name
                packages_content += str(pkg.package) + "\n"
            with open(overrides_file, 'w') as ofh:
                ofh.write(overrides_content)
            with open(package_file, 'w') as pfh:
                pfh.write(packages_content)
            with open(package_file, 'rb') as fhi, gzip.open(package_file_gz, 'wb') as fhgz, bz2.BZ2File(package_file_bz2, 'wb', compresslevel=9) as fhbz:
                shutil.copyfileobj(fhi, fhgz)
                fhi.seek(0)
                shutil.copyfileobj(fhi, fhbz)
                
            # Cleanup overrides file is silly
            os.remove(overrides_file)


        # Make Release
        pack = self._find_package_files(self._repodir)
        package_md5sums = '\n'.join([ ' '.join(x['md5sum']) for x in pack.values() ])
        package_sha1sums = '\n'.join([ ' '.join(x['sha1']) for x in pack.values() ])
        package_sha256sums = '\n'.join([ ' '.join(x['sha256']) for x in pack.values() ])
        release_file = os.path.join(self._repodir, 'Release')
        release_content = deb822.Release({'Suite': switches['reponame'],
                                         'Version': '1.0',
                                         'Component': 'main',
                                         'Origin': 'SAS',
                                         'Label': 'sas-esp-%s' % switches['arch'],
                                         'Architecture': switches['arch'],
                                         'Date': time.strftime('%a %b %T %Z %Y'),
                                         'MD5Sum': package_md5sums,
                                         'SHA1': package_sha1sums,
                                         'SHA256' : package_sha256sums,
                                         })

        with open(release_file, 'w') as fhr:
            fhr.write(str(release_content))

        # FIXME Sign the Release file

        return release_content

    def sign(self):
        raise NotImplementedError

