"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

import os

def find_storage_volume(search_dir = '/Volumes', name_filter="",
                        key_file="traces.cfg"):
    """
    Check if external drive is mounted before saving version files, looking for
    drives with a particular name, key file, or both

    search_dir: (str) dir to look for storage dir
    name_filter: (str) substring of volume name authenticating storage dir
    key_file: (str) file authenticating storage dir
    """
    name_match_dirs = list(filter(lambda x: name_filter in x, os.listdir(search_dir)))
    name_match_dirs = list(map(lambda x: os.path.join(search_dir, x), name_match_dirs))
    mounted_volumes = list(filter(lambda x: os.path.ismount(x), name_match_dirs))

    for volume in mounted_volumes:
        try:
            key_files = list(filter(lambda x: key_file == x, os.listdir(volume)))
            if len(key_files) >= 1:
                return volume
        except:
            raise
    return False
