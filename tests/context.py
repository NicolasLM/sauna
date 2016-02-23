import os
import sys

try:
    from unittest import mock
except ImportError:
    # Python 3.2 does not have mock in the standard library
    import mock

sys.path.insert(0, os.path.abspath('..'))

import sauna  # noqa
