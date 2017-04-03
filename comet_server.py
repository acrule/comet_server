"""
Adam Rule
March 29, 2017

Comet Server: Server extension paired with nbextension to track notebook use
Loosely based on https://github.com/Carreau/jupyter-book/blob/master/extensions/server_ext.py
"""

import os
import json
import pickle
import subprocess
import datetime
import sqlite3

import nbformat
from notebook.utils import url_path_join
from notebook.base.handlers import IPythonHandler, path_regex

class CometHandler(IPythonHandler):

    def get(self):
        """ check if extension loaded by visiting http://localhost:8888/comet """

        self.finish('Comet is working.')

    def post(self, path=''):
        """ Recieve and save data about notebook events
        path: relative path to notebook requesting the POST """

        post_data = self.get_json_body()
        os_path = self.contents_manager._get_os_path(path)
        save_changes(os_path, post_data)

def save_changes(os_path, event_data):
    """ save copy of notebook to an external drive
    os_path: path to notebook as saved on the operating system
    event_data: event data """

    volume = find_storage_volume()
    if not volume:
        print("Could not find external volume to save copy of notebook")
    else:

        # get the notebook in the correct format
        nb = nbformat.from_dict(event_data['model'])

        # get all our file names in order
        os_dir, fname = os.path.split(os_path)
        fname, file_ext = os.path.splitext(fname)
        dest_dir = os.path.join(volume, fname)
        version_dir = os.path.join(dest_dir, "versions")
        dbname = os.path.join(dest_dir, fname + ".db")
        dest_fname = os.path.join(dest_dir, fname + ".ipynb")
        date_string = datetime.datetime.now().strftime("-%Y-%m-%d-%H-%M-%S")
        ver_fname = os.path.join(version_dir, fname + date_string + ".ipynb")

        # if needed, create storage directories on the external volume
        if not os.path.isdir(dest_dir):
            create_dir(dest_dir)
            create_dir(version_dir)

        # save event to the database
        save_event(event_data, dbname)

        # TODO test comparison of outputs
        # TODO build way to read from external server
        # save the file if different from last version
        if os.path.isfile(dest_fname):
            if same_notebook(nb, dest_fname, True):
                return

        # save the current file to the external volume for future comparison
        nbformat.write(nb, dest_fname, nbformat.NO_CONVERT)

        # and save a time-stamped version periodically
        if not saved_recently(version_dir):
            nbformat.write(nb, ver_fname, nbformat.NO_CONVERT)

        # TODO find a way to supress .communicate() printing to stdout as
        # it clutters the terminal
        # track file changes with git
        in_out = verify_git_repository(dest_dir)
        p1 = subprocess.Popen(["git", "add", fname + ".ipynb"], cwd=dest_dir)
        in_out = p1.communicate()
        p2 = subprocess.Popen(["git", "commit", "-m", "'Commit'"], cwd=dest_dir)

def find_storage_volume(search_dir = '/Volumes', namefilter="", key_file="traces.cfg"):
    """
    Check if external drive is mounted before saving version files, looking for
    drives with a particular name, key file, or both

    search_dir: dir to look for storage dir
    namefilter: substring of volume name authenticating storage dir
    key_file: file authenticating storage dir
    """
    for d in os.listdir(search_dir):
        if namefilter in d:
            volume = os.path.join(search_dir, d)
            if (os.path.ismount(volume)):
                try:
                    subdirs = os.listdir(volume)
                    for fname in subdirs:
                        if key_file == fname:
                            return volume
                except:
                    pass
    return False

def save_event(event_data, db):
    """
    save event to sqlite database

    db: path to database
    """

    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS events (time integer, name text, cell_index text)''') #id integer primary key autoincrement,
    tuple_event = (str(event_data['time']), event_data['name'], str(event_data['index'])) #pickle.dumps(event_data['cell']))
    c.execute('INSERT INTO events VALUES (?,?,?)', tuple_event)
    conn.commit()
    conn.close()

def same_notebook(nb1, nb2, compare_outputs = False):
    """ Check if two Jupyter notebooks are essentailly the same
    (e.g. same inputs, same outputs, or both)

    nb1: model data for first notebook
    nb2: file path to second notebook
    compare_outputs: boolean of whether to compare outputs in addition to inputs """

    cells1 = nb1['cells']
    cells2 = nbformat.read(nb2, nbformat.NO_CONVERT)['cells']

    # first check that number of cells match
    if len(cells1) != len(cells2):
        return False

    # then check that the types of cells match
    for i in range(len(cells1)):
        if cells1[i]["cell_type"] != cells2[i]["cell_type"]:
            return False

    # then check that the cell input, or source, matches for each cell
    for i in range(len(cells1)):
        if cells1[i]["source"] != cells2[i]["source"]:
            return False

    # finally, check the outputs
    #TODO disregard meaningless differences, such as different name of
    # inline matplotlib graph due to being saved in a different memory
    # locations (e.g., "0x10ccdf4a8" v. "0x10c9dc7b8")
    if compare_outputs:
        for i in range(len(cells1)):
            # only compare code cell outputs
            if cells1[i]["cell_type"] == "code" and cells2[i]["cell_type"] == "code":
                # ensure same number of outputs
                if len(cells1[i]['outputs']) != len(cells2[i]['outputs']):
                    print("outputs not the same length")
                    return False
                # and for all outputs for each cell
                if len(cells1[i]['outputs']) > 0 and len(cells2[i]['outputs']) > 0:
                    for j in range(len(cells1[i]['outputs'])):
                        # check that the output type matches
                        if cells1[i]['outputs'][j]['output_type'] != cells2[i]['outputs'][j]['output_type']:
                            print("output types do not match")
                            return False

                        # and that the relevant data matches
                        if cells1[i]['outputs'][j]['output_type'] in ["display_data","execute_result"]:
                            if cells1[i]['outputs'][j]['data'] != cells2[i]['outputs'][j]['data']:
                                print("display/execute does not match")
                                return False
                        elif cells1[i]['outputs'][j]['output_type'] == "stream":
                            if cells1[i]['outputs'][j]['text'] != cells2[i]['outputs'][j]['text']:
                                print("stream does not match")
                                return False
                        elif cells1[i]['outputs'][j]['output_type'] == "error":
                            if cells1[i]['outputs'][j]['evalue'] != cells2[i]['outputs'][j]['evalue']:
                                print("error does not match")
                                return False

    return True

def saved_recently(version_dir, min_time=60):
    """ check if a previous version of the file has been saved recently

    version_dir: dir to look for previous versions
    min_time: minimum time in seconds allowed between saves """

    #TODO check for better way to get most recent file in dir, maybe using glob
    #TODO filter file list to only include .ipynb
    versions = [f for f in os.listdir(version_dir) if os.path.isfile(os.path.join(version_dir, f))]
    if len(versions) > 0:
        vdir, vname = os.path.split(versions[-1])
        vname, vext = os.path.splitext(vname)
        last_time_saved = datetime.datetime.strptime(vname[-19:], "%Y-%m-%d-%H-%M-%S")
        delta = (datetime.datetime.now() - last_time_saved).seconds

        if delta <= min_time:
            return True
        else:
            return False
    else:
        return False

def create_dir(directory):
    try:
        os.makedirs(directory)
    except OSError:
        pass

def verify_git_repository(directory):
    if '.git' not in os.listdir(directory):
        p = subprocess.Popen(['git','init'], cwd=directory)
        return p.communicate()
    else:
        return False

def load_jupyter_server_extension(nb_app):
    """ Load the extension and set up routing to proper handler
    nb_app: Jupyter Notebook Application """

    nb_app.log.info('Comet Server extension loaded')
    web_app = nb_app.web_app
    host_pattern = '.*$'
    route_pattern = url_path_join(web_app.settings['base_url'], r"/api/comet%s" % path_regex)
    web_app.add_handlers(host_pattern, [(route_pattern, CometHandler)])
