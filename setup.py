"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

from distutils.core import setup

setup(
    name='comet_server',
    version='0.1',
    py_modules=['comet_server',
                'comet_dir',
                'comet_diff',
                'comet_git',
                'comet_sqlite',                
                'comet_viewer'],
    url = 'https://github.com/activityhistory/comet_server'
)
