from distutils.core import setup
import py2exe

globs = {}
execfile('pbp/version.py', globs)
version = globs['version']

setup_args = dict(name="pbp", author="Cory Dodt", 
                  author_email='corydodt@twistedmatrix.com',
                  url='http://localhost/FIXME',
                  version=version,
                  scripts=['pbpscript'], packages=['pbp'])



setup(**setup_args)
