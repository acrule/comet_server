from setuptools import setup

setup(
    name='comet_server',
    version='0.1',
    scripts=['comet_server.py',
                'comet_diff.py',
                'comet_git.py',
                'comet_sqlite.py',
                'comet_volume.py'],
    url = 'https://github.com/activityhistory/comet_server'
)