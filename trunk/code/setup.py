from distutils.core import setup
try:
    import py2exe
except ImportError:
    pass
globs = {}
try:
    execfile('_version.py', globs)
    version = globs['version']
except EnvironmentError:
    execfile('pbp/version.py', globs)
    version = globs['version']


setup_args = dict(name="pbp", author="Cory Dodt", 
                  author_email='corydodt@twistedmatrix.com',
                  url='http://localhost/FIXME',
                  version=version,
                  scripts=['pbpscript'], packages=['pbp'])



setup(**setup_args)
