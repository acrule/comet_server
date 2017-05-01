"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

import os
import json
import datetime

import nbformat
import nbconvert
from notebook.utils import url_path_join
from notebook.base.handlers import IPythonHandler, path_regex

from comet_diff import get_diff_at_indices
from comet_git import verify_git_repository, git_commit
from comet_sqlite import record_action_to_db
from comet_volume import find_storage_volume, create_dir
from comet_viewer import get_viewer_html


class CometHandler(IPythonHandler):

    # check if extension loaded by visiting http://localhost:8888/api/comet
    def get(self, path=''):
        """
        Render a website visualizing the notebook's edit history

        path: (str) relative path to notebook requesting POST
        """
        
        data_dir = '/Volumes/TRACES' + path
        html = get_viewer_html(data_dir)
        self.write(html)

    def post(self, path=''):
        """
        Save data about notebook actions

        path: (str) relative path to notebook requesting POST
        """

        post_data = self.get_json_body()
        os_path = self.contents_manager._get_os_path(path)
        save_changes(os_path, post_data)
        self.finish(json.dumps({'msg': path}))

def save_changes(os_path, action_data, track_git=True, track_versions=True,
                track_actions=True):
    """
    Track notebook changes with git, periodic snapshots, and action tracking

    os_path: (str) path to notebook as saved on the operating system
    action_data: (dict) action data in the form of
        t: (int) time action was performed
        name: (str) name of action
        index: (int) selected index
        indices: (list of ints) selected indices
        model: (dict) notebook JSON
    track_git: (bool) use git to track changes to the notebook
    track_versions: (bool) periodically save full versions of the notebook
    track_actions: (bool) track individual actions performed on the notebook
    """

    volume = find_storage_volume()

    if not volume:
        print("Could not find external volume to save Comet data")

    else:
        # generate file names
        os_dir, fname = os.path.split(os_path)
        fname, file_ext = os.path.splitext(fname)
        dest_dir = os.path.join(volume, fname)
        version_dir = os.path.join(dest_dir, "versions")
        dbname = os.path.join(dest_dir, fname + ".db")
        dest_fname = os.path.join(dest_dir, fname + ".ipynb")
        date_string = datetime.datetime.now().strftime("-%Y-%m-%d-%H-%M-%S-%f")
        ver_fname = os.path.join(version_dir, fname + date_string + ".ipynb")
        
        # get the notebook in the correct format (nbnode)
        current_nb = nbformat.from_dict(action_data['model'])

        # if needed, create storage directories on the external volume
        if not os.path.isdir(dest_dir):
            create_dir(dest_dir)
            create_dir(version_dir)

        # save information about the action to an sqlite database
        if track_actions:
            record_action_to_db(action_data, dest_fname, dbname)

        # save file versions and check for changes only if different from last notebook
        if os.path.isfile(dest_fname):
            all_cells = list(range(len(current_nb['cells']))) # check all cells
            diff = get_diff_at_indices(all_cells, action_data, dest_fname, True)
            if not diff:
                return

        # save the current file to the external volume for future comparison
        nbformat.write(current_nb, dest_fname, nbformat.NO_CONVERT)

        # save a time-stamped version periodically
        if track_versions:
            if not was_saved_recently(version_dir):
                nbformat.write(current_nb, ver_fname, nbformat.NO_CONVERT)

        # track file changes with git
        if track_git:
            try:
                verify_git_repository(dest_dir)
                git_commit(fname, dest_dir)
            except:
                pass

def was_saved_recently(version_dir, min_time=60):
    """ check if a previous version of the file has been saved recently

    version_dir: (str) dir to look for previous versions
    min_time: (int) minimum time in seconds allowed between saves """

    versions = [f for f in os.listdir(version_dir)
        if os.path.isfile(os.path.join(version_dir, f)) 
        and f[-6:] == '.ipynb']
    if len(versions) > 0:
        vdir, vname = os.path.split(versions[-1])
        vname, vext = os.path.splitext(vname)
        last_time_saved = datetime.datetime.strptime(vname[-26:], "%Y-%m-%d-%H-%M-%S-%f")
        delta = (datetime.datetime.now() - last_time_saved).seconds
        return delta <= min_time
    else:
        return False

def load_jupyter_server_extension(nb_app):
    """
    Load the extension and set up routing to proper handler

    nb_app: (obj) Jupyter Notebook Application
    """

    nb_app.log.info('Comet Server extension loaded')
    web_app = nb_app.web_app
    host_pattern = '.*$'
    route_pattern = url_path_join(web_app.settings['base_url'],
                                    r"/api/comet%s" % path_regex)
    web_app.add_handlers(host_pattern, [(route_pattern, CometHandler)])
