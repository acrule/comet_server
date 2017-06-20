"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

from distutils.core import setup

setup(
    name='comet_server',
    version='0.1',
    description='Server-side extension for tracking use of Jupyter Notebook',
    author='Adam Rule',
    author_email='acrule@ucsd.edu',
    url = 'https://github.com/activityhistory/comet_server',
    packages=['comet_server']    
)
