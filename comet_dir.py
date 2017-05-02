"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

import os
import json

def find_storage_dir():
    filename = os.path.expanduser('~/.jupyter/nbconfig/notebook.json')
    storage_dir = default_storage_dir()
    if os.path.isfile(filename):
        with open(filename) as data_file:    
            data = json.load(data_file)
            if data["Comet"]["data_directory"]:
                storage_dir = data["Comet"]["data_directory"]
    return storage_dir
    
def default_storage_dir():
    return os.path.expanduser('~/.jupyter/comet_data')
            
def create_dir(directory):
    try:
        os.makedirs(directory)
    except OSError:
        pass
