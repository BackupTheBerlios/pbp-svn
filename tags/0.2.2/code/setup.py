from distutils.core import setup
from distutils.command.install_data import install_data 
class smart_install_data(install_data): 
    def finalize_options (self):
        self.set_undefined_options('install',
            ('install_lib', 'install_dir')
        )
        install_data.finalize_options(self)

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
                  scripts=['pbpscript'], packages=['pbp'],
                  data_files = [('pbp', ['pbp/wwwsearch.zip',])],
                  cmdclass = dict(install_data = smart_install_data,
                                  ),
                  )



setup(**setup_args)
