#!/usr/bin/env python

'''
Python implementation to extract info from .deb

If it fails you get to keep the pieces

pip install python-debian chardet

'''

import os
import sys
import argparse

try:
    from debian import debfile
except Exception:
    print("[ERROR] Failed to import debian\npip install python-debian chardet\n")
    sys.exit()

try:
    # Can't check version so need to support xz
    assert 'xz' in debfile.PART_EXTS
except Exception:
    print("[ERROR] python-debian missing xz support\npip install --upgrade python-debian chardet\n")
    sys.exit()

from pkg import DebPkg

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
                  


def apt_repo_utils(args=None):

    __version__ = '0.0.1'
    _usage = ('%(prog)s [options] /path/*.deb\n')
    _description = ("Apt Repository Creation Tool\n"
                    "Python implementation of apt repo tools\n"
                    )
    _prog = "create_apt_repo"

    parser = argparse.ArgumentParser(version="%(prog)s " + __version__,
                                     description=_description,
                                     usage=_usage,
                                     prog=_prog
                                     )

    parser.add_argument("-c", "--create", dest="create", action="store_true",
                        default=False,
                        help="Create apt repository metadata")

    parser.add_argument("-i", "--index", dest="index", action="store_true",
                        default=False,
                        help="Index apt repository metadata")

    parser.add_argument("-p", "--parse", dest="parse", action="store_true",
                        default=False,
                        help="Parse apt repository metadata")

    parser.add_argument("-r", "--reponame", dest="reponame", action="store",
                        default="stable",
                        help="Specify apt repository name")

    parser.add_argument("-a", "--arch", dest="arch", action="store",
                        default="amd64",
                        help="Specify apt repository name")

    parser.add_argument('debpkgs', nargs='?',
                        help="/path/to/pkg.deb pkg.deb... etc")

    args = parser.parse_args()

    ops = {
        'create': args.create,
        'index': args.index,
        'parse': args.parse,
    }

    switches = {
        'reponame': args.reponame,
        'arch': args.arch,
    }

    if True not in ops.values():
        ops['parse'] = True

    files = []

    pool = 'pool/main'

    if args.debpkgs:
        files = args.debpkgs

    # if True not in steps.values():
    #    steps['package'] = True

    if ops['create']:
        if not os.path.exists(pool) and files:
            os.makedirs(pool)
            for f in files:
                shutil.copy(f, pool)

    if ops['index'] or ops['parse']:
        if not os.path.exists(pool):
            print("[ERROR] No pool/main directory or *.deb supplied")
            print("%s --help" % _prog)
            sys.exit(1)

    pool_files = [os.path.join(pool, x)
                  for x in os.listdir(pool) if x.endswith('.deb')]

    packages = {}

    for path in pool_files:
        pkg = DebPkg.from_file(path)
        packages.setdefault(pkg.name, pkg)

    if ops['index']:
        print("Indexing %s" % switches['reponame'])

        repodir = os.path.join('dists', switches['reponame'])

        bindirs = []
        for root, dirs, _ in os.walk(repodir): 
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
            # Index of packages is written to Packages which is also zipped
            # dpkg-scanpackages -a ${arch} pool/main $overrides_file > $package_file
            # The line above is also commonly written as:
            # dpkg-scanpackages -a ${arch} pool/main /dev/null > $package_file

            # gzip -9c $package_file > ${package_file}.gz
            # with open(package_file, 'rb') as fhi, gzip.open(package_file_gz, 'wb') as fhgz:
            #    shutil.copyfileobj(fhi, fhgz)
            # with open(package_file, 'rb') as fhi, bz2.BZ2File(package_file_bz2, 'wb', compresslevel=9) as fhbz:
            #    shutil.copyfileobj(fhi, fhbz)

            # bzip2 -c $package_file > ${package_file}.bz2
            with open(package_file, 'rb') as fhi, gzip.open(package_file_gz, 'wb') as fhgz, bz2.BZ2File(package_file_bz2, 'wb', compresslevel=9) as fhbz:
                shutil.copyfileobj(fhi, fhgz)
                fhi.seek(0)
                shutil.copyfileobj(fhi, fhbz)
                
            # Cleanup
            os.remove(overrides_file)

        def _find_packages(path):
            files = {}
            index = len(path.split(os.sep))
            for root, _, f in os.walk(path):
                for name in f:
                    if name.startswith('Package'):
                        full_path = os.path.join(root,name)
                        short_path = os.sep.join(full_path.split(os.sep)[index:])
                        hashes = DebPkg.make_hashes(os.path.abspath(full_path))
                        size = str(os.stat(full_path).st_size)

                        info = { 
                            "md5sum": [ hashes["MD5sum"], size, short_path ],
                            "sha1": [ hashes["SHA1"], size, short_path ],
                            "sha256": [ hashes["SHA256"], size, short_path ],
                        }
                        files.setdefault(short_path, info)
            return files



        # Make Release
        pack = _find_packages(repodir)
        package_md5sums = '\n'.join([ ' '.join(x['md5sum']) for x in pack.values() ])
        package_sha1sums = '\n'.join([ ' '.join(x['sha1']) for x in pack.values() ])
        package_sha256sums = '\n'.join([ ' '.join(x['sha256']) for x in pack.values() ])
        release_file = os.path.join(repodir, 'Release')
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

        import epdb;epdb.st()


if __name__ == "__main__":
    main()
