import os
import hashlib

BLOCKSIZE = 65536

class Hasher(object):

    def __init__(self, algorithms=[]):
        if isinstance(algorithms, str):
            algorithms = [ algorithms ]
        self.algorithms = tuple(algorithms) or hashlib.algorithms
        self.hashers = dict([ (x, getattr(hashlib, x)) for x in hashlib.algorithms if x in self.algorithms ] )
        self._digests = dict([(x, None) for x in self.hashers.keys()])

    def _hash(self):
        raise NotImplementedError

    def _make_hashes(self):
        if None in self._digests.values():
            for k, hasher in self.hashers.items():
                self._digests[k] = self._hash(hasher())

    @property
    def available(self):
        return self.algorithms

    @property
    def digests(self):
        self._make_hashes()
        return self._digests

    def read(self):
        raise NotImplementedError

    def write(self):
        raise NotImplementedError

class HashString(Hasher):

    def __init__(self, data, algorithms=[]):
        self.data = data
        super(HashString, self).__init__(algorithms=algorithms)

    def _hash(self, hasher):
        hasher.update(self.data)
        return hasher.hexdigest()

class HashFile(Hasher):

    def __init__(self, path, algorithms=[]):
        self.path = path
        self.filename = os.path.basename(self.path)
        self.digest_path = '.'.join([self.path, 'chksums'])
        super(HashFile, self).__init__(algorithms=algorithms)

    def _hash(self, hasher):
        with open(self.path, 'rb') as fh:
            buf = fh.read(BLOCKSIZE)
            while len(buf) > 0:
                hasher.update(buf)
                buf = fh.read(BLOCKSIZE)
        return hasher.hexdigest()
 
    @property
    def digest_lines(self):
        '''
        BSD Style for use in single file
        '''
        self._make_hashes()
        lines = ""
        template = "{0} ({1}) = {2}\n"
        for k, v in self.digests.items():
            lines += template.format(k.capitalize(), self.filename, v)
        return lines

    def write(self):
        self._make_hashes()
        with open(self.digest_path, 'w') as fh:
            fh.write(self.digest_lines)
        return self.digest_path

# UTILS

def hash_file(path, algs=['md5', 'sha1', 'sha256']):
    hasher = HashFile(path, algorithms=algs)
    return hasher.digests

def deb_hash_file(path):
    '''
    Apt Package File uses different syntax
    '''
    hasher = HashFile(path, algorithms=['md5', 'sha1', 'sha256'])
    hashes = {'MD5sum': hasher.digests['md5'],
              'SHA1':  hasher.digests['sha1'],
              'SHA256':  hasher.digests['sha256'],
            }
    return hashes

def hash_string(data, algs=['md5', 'sha1', 'sha256']):
    hasher = HashString(data, algorithms=algs)
    return hasher.digests

