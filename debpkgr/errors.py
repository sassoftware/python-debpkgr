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


import traceback
import pdb


class DebPkgError(Exception):
    "Base class"

class InvalidTest(DebPkgError):
    "Raised when YAML is invalid"

class SourceBuildError(DebPkgError):
    "Raised when building the source artifact fails"


class BinaryBuildError(DebPkgError):
    "Raised when building the binary artifact fails"


class InvalidKeyError(DebPkgError):
    """An invalid key was specified"""

class KeyNotFoundError(DebPkgError):
    """The specified key was not found"""


def debug_except_hook(type, value, tb):
    print "T-Rex Hates %s" % type.__name__
    print str(type)
    traceback.print_exception(type, value, tb)
    pdb.post_mortem(tb)
