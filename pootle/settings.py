# -*- coding: utf-8 -*-
#
# Copyright (C) Pootle contributors.
#
# This file is a part of the Pootle project. It is distributed under the GPL3
# or later license. See the LICENSE file for a copy of the license and the
# AUTHORS file for copyright and authorship information.

import glob
import os


WORKING_DIR = os.path.abspath(os.path.dirname(__file__))


def working_path(filename):
    """Return an absolute path for :param:`filename` by joining it to
    ``WORKING_DIR``.
    """
    return os.path.join(WORKING_DIR, filename)


conf_files_path = os.path.join(WORKING_DIR, 'settings', '*.conf')
conf_files = sorted(glob.glob(conf_files_path))

for f in conf_files:
    conf_path = os.path.abspath(f)
    with open(conf_path, encoding='utf-8') as conf_fh:
        exec(compile(conf_fh.read(), conf_path, 'exec'), globals())
