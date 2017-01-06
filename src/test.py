#!/usr/bin/env python

import yaml
import onepm

filenames = [ 'package_deb.yaml', 'package_foo.yaml', 'package_foo-0.0.2.yaml', 'package_default.yaml' ]

templates = {}

for filename in filenames:
    with open(filename, 'r') as fh:
        print("Reading from {0}".format(filename))
        package = onepm.new_package(fh)

    templates.setdefault(filename, package.to_templates())

import epdb;epdb.st()
