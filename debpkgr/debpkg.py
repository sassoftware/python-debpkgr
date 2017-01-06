#!/usr/bin/env python

'''
Python implementation to extract info from .deb

If it fails you get to keep the pieces

pip install python-debian chardet

'''

import os
import hashlib
import sys
import argparse

try:
    from debian import debfile
    from debian import deb822
except Exception:
    print("[ERROR] Failed to import debian\npip install python-debian chardet\n")
    sys.exit()

try:
    # Can't check version so need to support xz
    assert 'xz' in debfile.PART_EXTS
except Exception:
    print("[ERROR] python-debian missing xz support\npip install --upgrade python-debian chardet\n")
    sys.exit()

class DebPkgFiles(list):
    def __new__(cls, data=None):
        obj = super(DebPkgFiles, cls).__new__(cls, data)
        return obj
    def __repr__(self):
        return 'DebPkgFiles(%s)' % list(self)
    def __str__(self):
        return '\n'.join(list(self))

class DebPkgMD5sums(deb822.Deb822):
    def __str__(self):
        results = ""
        for k, v in self.items():
            results += "%s %s\n" % (k,v)
        return results
        

class DebPkg(object):
    __slots__ = ("_c", "_h", "_md5")

    def __init__(self, control, hashes, md5sums):
        if isinstance(control, deb822.Deb822):
            self._c = control
        else:
            self._c = deb822.Deb822(control)
        if isinstance(hashes, deb822.Deb822):
            self._h = hashes
        else:
            self._h = deb822.Deb822(hashes)
        if isinstance(md5sums, DebPkgMD5sums):
            self._md5 = md5sums
        else:
            self._md5 = DebPkgMD5sums(md5sums) 
       
    @property
    def package(self):
        package = self._c
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
        return '_'.join([self._c['Package'], self._c['Version'], self._c['Architecture']])

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
        BLOCKSIZE = 65536
        def _hash(hasher):
            with open(path, 'rb') as fh:
                buf = fh.read(BLOCKSIZE)
                while len(buf) > 0:
                    hasher.update(buf)
                    buf = fh.read(BLOCKSIZE)
            return hasher.hexdigest()
        hashes = {'MD5sum': hashlib.md5(),
                  'SHA1':  hashlib.sha1(),
                  'SHA256':  hashlib.sha256(),
                  }
        results = {}
        for tag, hasher in hashes.items():
            results.setdefault(tag, _hash(hasher))
        return results

    @classmethod
    def from_file(cls, path):
        debpkg = debfile.DebFile(filename=path)
        md5sums = debpkg.md5sums()
        control = debpkg.control.debcontrol()
        hashes = cls.make_hashes(path)
        return cls(control, hashes, md5sums)

def main(args=None):

    __version__ = '0.0.1'
    _usage = ('%(prog)s [options] pkg.deb\n')
    _description = ("Debian Package Infromation Tool\n"
                "Python implementation of dpkg tools\n"
            )
    _prog = "debpkg"

    parser = argparse.ArgumentParser(version="%(prog)s " + __version__,
                                        description=_description,
                                        usage=_usage,
                                        prog=_prog
                                )

    parser.add_argument("-p", "--Package", dest="package", action="store_true",
                    default=False,
                    help="Return apt style Package information")

    parser.add_argument("-n", "--name", dest="name", action="store_true",
                    default=False,
                    help="Return .deb Package Name")

    parser.add_argument("-N", "--nvra", dest="nvra", action="store_true",
                    default=False,
                    help="Return .deb Package nvra")

    parser.add_argument("-f", "--files", dest="files", action="store_true",
                    default=False,
                    help="Return .deb Package File List")

    parser.add_argument("-F", "--file-md5sums", dest="md5sums", action="store_true",
                    default=False,
                    help="Return .deb Package File List with MD5sums")
    
    parser.add_argument("--md5sum", dest="md5sum", action="store_true",
                    default=False,
                    help="Return .deb Package MD5sum")

    parser.add_argument("--sha1", dest="sha1", action="store_true",
                    default=False,
                    help="Return .deb Package sha1")

    parser.add_argument("--sha256", dest="sha256", action="store_true",
                    default=False,
                    help="Return .deb Package sha256")

    parser.add_argument('debpkgs', nargs='?',
                    help="/path/to/pkg.deb pkg.deb... etc")

    args = parser.parse_args()

    steps = {   'md5sum' : args.md5sum,
                'sha1' : args.sha1,
                'sha256' : args.sha256,
                'package' : args.package,
                'name' : args.name,
                'nvra' : args.nvra,
                'files' : args.files,
                'md5sums' : args.md5sums,
        }
                

    if True not in steps.values():
        steps['package'] = True

    if not args.debpkgs:
        pool = 'pool/main'
        if os.path.exists(pool):
            files = [os.path.join(pool, x)
                for x in os.listdir(pool) if x.endswith('.deb')]
        else:
            print("[ERROR] No pool/main directory or *.deb supplied")
            print("%s --help" % _prog)
            sys.exit(1)
    else:
        files = args.debpkgs

    packages = {}

    for fpath in files:
        pkg = DebPkg.from_file(fpath)
        packages.setdefault(pkg.name, pkg)

    for name, pkg in packages.items():
        for step in steps:
            if steps[step]:
                print(getattr(pkg, step))
                  

if __name__ == "__main__":
    main()
