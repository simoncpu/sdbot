import sys
import os

PYTHON3 = sys.version_info[0] > 2


def decode(str_, codec='utf8'):
    """decode a string. if str is a python 3 string, do nothing."""
    if PYTHON3:
        return str_
    else:
        return str_.decode(codec)


def encode(str_, codec='utf8'):
    """encode a string. if str is a python 3 string, do nothing."""
    if PYTHON3:
        return str_
    else:
        return str_.encode(codec)


def relevant_environ():
    return dict((key, os.environ[key])
                for key in os.environ
                if key.startswith("SLACK") or key.startswith("LIMBO"))


def strip_extension(lst):
    return (os.path.splitext(l)[0] for l in lst)


def getif(config, name, envvar):
    if envvar in os.environ:
        config[name] = os.environ.get(envvar)
