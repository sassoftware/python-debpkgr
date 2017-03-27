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

from __future__ import unicode_literals
import codecs
import os
import re
import string
from collections import namedtuple

from .compat import urlsplit
from .compat import urlretrieve
from .compat import HTTPError
from .errors import FileNotFoundError

ENV_NAME_RE = re.compile(r'_{2,}')
utf8writer = codecs.getwriter('utf-8')


DownloadRequest = namedtuple("DownloadRequest", "url destination data")


def local_path_from_url(url):
    res = urlsplit(url)
    if res.scheme == 'file' or not res.netloc:
        arr = []
        for s in (res.netloc, res.path):
            if s:
                arr.append(s)
        return ''.join(arr)
    return None


def _to_url(uri):
    res = urlsplit(uri)
    if not res.netloc:
        return 'file://' + os.path.abspath(uri)
    return uri


def opener(path, destination=None):
    fh = None
    msg = 'Failed to open %s with %s %s'
    url = _to_url(path)
    try:
        fh, _ = urlretrieve(url, filename=destination)
    except HTTPError as e:
        error = msg % (path, e.code, e.reason)
        raise FileNotFoundError(error)
    return fh


def download(requests):
    """
    Initiate multiple downloads.
    requests is a list of DownloadRequest objects.
    A DownloadRequest object contains:
    * url: source URL
    * destination: a destination file or file descriptor
    * data: additional information passed back to the caller at the end of the
    download.
    """
    for req in requests:
        dest = req.destination
        opener(req.url, dest)
    return requests


def makedirs(dirName):
    if os.path.isdir(dirName):
        return dirName
    try:
        os.makedirs(dirName, mode=0o755)
    except OSError as e:
        if e.errno != 17:
            raise
    return dirName


def normpath(path, follow_links=False):
    """Normalize a path.

    Expands user directories and environment variables, elimites double
    slashes, and converts the path to an absolute path. Optionally, it will
    resolve symlinks to the real path.

    :params str path: path to normalize
    :params bool follow_links: Whether to resolve symlinks
    :returns: a fully normalized path
    """
    path = os.path.expanduser(path)
    path = os.path.expandvars(path)
    path = os.path.normpath(path)
    if follow_links:
        path = os.path.realpath(path)
    return os.path.abspath(path)


def normenvname(s, uppercase=True):
    """:func:`normenvname` converts the string ``s`` into a proper environment
    variable name. Any whitespace or punctuation in ``s`` will be replaced with
    an underscore, and any repeated underscores will be collapsed into a single
    underscore.

    :param str s: string to convert
    :param bool uppercase: convert lower case letters to upper case if True
    :returns: converted string
    """
    envname_translator = get_translator(string.punctuation + string.whitespace)
    s = envname_translator(s)
    s = ENV_NAME_RE.sub('_', s)
    if uppercase:
        return s.upper()
    return s


def get_translator(translate_from, translate_to='_'):
    translation_table = dict((ord(c), translate_to) for c in translate_from)
    return lambda s: s.translate(translation_table)
