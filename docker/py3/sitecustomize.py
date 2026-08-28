# Phase 1: installed into site-packages (see docker/py3/Dockerfile) so
# Python's `site` module imports it automatically at interpreter
# startup - before pytest, before its plugins' own pytest11 entry
# points load (django-assets registers one of its own, independent of
# anything pootle imports), before anything else has a chance to hit
# the Python-3-vs-Django-1.11 incompatibilities pootle_py3_compat.py
# patches. This is the earliest hook available; conftest.py and
# pootle/__init__.py are both too late for some import orderings.
#
# Deliberately imports the standalone top-level pootle_py3_compat
# module, not anything under `pootle.*`: importing a `pootle`
# submodule this early would run pootle/__init__.py and mark the
# `pootle` package as already-imported in sys.modules before pytest's
# assertion-rewrite import hook installs, which pytest reports as a
# warning - fatal, given setup.cfg's filterwarnings = error.
import pootle_py3_compat  # noqa
