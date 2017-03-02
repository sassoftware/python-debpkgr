debpkgr
=======

Pure Python implementation of Debian/Ubuntu packaging and repository utilities.

The allows one to perform various Debian-specific operations on
non-Debian systems, in the absence of typical system-provided
utilities (e.g. apt).

Example
=======

Inspect Package
---------------

.. code:: python

 from debpkgr.debpkg import DebPkg

 pkg = DebPkg.from_file('/path/to/foo.deb')

 print(pkg.name)
 print(pkg.nvra)
 print(pkg.md5sum)
 print(pkg.package)

Create Repo
-----------

.. code:: python

 from debpkgr.aptrepo import create_repo

 name = 'test_repo_foo'
 arches = ['amd64', 'i386']
 description = 'Apt repository for Test Repo Foo'

 files = []
 for root, _, fl in os.walk(temp_dir):
     for f in fl:
         if f.endswith('.deb'):
             files.append(os.path.join(root, f))

 repo = create_repo(self.new_repo_dir, files, name=name,
                    arches=arches, desc=description)

Signature Support
-----------------

It is possible to sign the repository metadata using a wrapper script /
executable around GPG or another GPG-signing facility (like a [Hardware Security Module](https://en.wikipedia.org/wiki/Hardware_security_module).

To do so, you will need to pass a `SignOptions` object to the lower-level
`AptRepo` class as the `gpg_sign_options` argument:

.. code:: python

    gpg_sign_options = SignOptions(cmd="/usr/local/bin/sign.sh",
                                   key_id="45BA0816")
    repo = AptRepo(repo_dir, repo_name,
                   gpg_sign_options=gpg_sign_options)

The supplied sign command has to be an executable.

It will be supplied the path to a `Release` file to be signed, and is
expected to produce a file named `Release.gpg` in the same directory as the
`Release` file.

Additionally, the sign command will be passed the following environment
variables:

* `GPG_CMD`
* `GPG_KEY_ID` (if specified in the configuration file)
* `GPG_REPOSITORY_NAME`
* `GPG_DIST`

The sign command may decide on a key ID to use, based on the repository name
or the dist that is being signed.

A minimal sign command using GPG could be:

.. code:: shell

    #!/bin/bash -e

    KEYID=${GPG_KEY_ID:-45BA0816}

    gpg --homedir /var/lib/debpkgr/gpg-home \
        --detach-sign --default-key $KEYID \
        --armor --output ${1}.gpg ${1}

You could import your password-less GPG keys like this:

.. code:: shell

    mkdir /var/lib/debpkgr/gpg-home
    chmod 0700 /var/lib/debpkgr/gpg-home
    gpg --homedir /var/lib/debpkgr/gpg-home --import <path-to-secret-keys>
