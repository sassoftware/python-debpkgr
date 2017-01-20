debpkgr
=======

Debian/Ubuntu utils including apt repo creation and .deb package info


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




Reference
==========

Tag
----
Setup gpg keys

Tag and sign

  ``git tag -sm 'v0.0.1' 0.0.1``

Push tags

  ``git push -u origin master``

building
--------

Configure pypi local

::

 cat > ~/.pypirc << EOF
 [distutils]
 index-servers =
    pypi-local
 [pypi-local]
 repository: https://svcartifact.unx.sas.com/artifactory/api/pypi/pypi-local
 username: <username>
 password: <password>

 EOF


Build wheel

  ``pip install wheel``

  ``python setup.py sdist bdist_wheel upload -r pypi-local``


Install
-------

  ``pip install debpkgr -i https://svcartifact.unx.sas.com/artifactory/api/pypi/pypi/simple``


:Authors:
    Brett Smith

:Version: 0.0.1
