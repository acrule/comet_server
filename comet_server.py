"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

import os
import cgi
import json
import datetime

import nbformat
import nbconvert
from notebook.utils import url_path_join
from notebook.base.handlers import IPythonHandler, path_regex

from comet_diff import get_diff_at_indices
from comet_git import verify_git_repository, git_commit
from comet_sqlite import record_action_to_db
from comet_volume import find_storage_volume


class CometHandler(IPythonHandler):

    # check if extension loaded by visiting http://localhost:8888/api/comet
    def get(self, path=''):
        vol = '/Volumes/TRACES' + path
        versions_path = os.path.join(vol, 'versions')

        if os.path.isdir(versions_path):
            versions = [f for f in os.listdir(versions_path)
                if os.path.isfile(os.path.join(versions_path, f))
                and f[-6:] == '.ipynb']

            html = get_html(versions)
            if  '<body></body>' not in html:    #i.e. if there is any body
                self.finish(html)
            else:
                self.finish('<h1>No Data</h1> There is no data saved for %s' % path)
        else:
            self.finish('<h1>No Data</h1> There is no data saved for %s' % path)

    def post(self, path=''):
        """
        Save data about notebook actions

        path: (str) relative path to notebook requesting POST
        """

        post_data = self.get_json_body()
        os_path = self.contents_manager._get_os_path(path)
        save_changes(os_path, post_data)
        self.finish(json.dumps({'msg': path}))

    def get_html(versions):
        html = '<html><head><style>\
                body{ width: 20000px;}\
                .wrap { width: 320px; height: 4000px; padding: 0; overflow: hidden; float: left;}\
                .frame { width: 1280px; height: 12000px; border: 1px solid black}\
                .frame { \
                -moz-transform: scale(0.25); \
                -moz-transform-origin: 0 0; \
                -o-transform: scale(0.25); \
                -o-transform-origin: 0 0; \
                -webkit-transform: scale(0.25); \
                -webkit-transform-origin: 0 0; \
                } \
                </style></head><body>'

        for v in versions:
            nb_path = os.path.join(versions_path, v)
            html_path = nb_path[:-6] + '.html'

            html_exporter = nbconvert.HTMLExporter()
            (body, resources) = html_exporter.from_file(nb_path)
            escaped_html = cgi.escape(body, True)

            frame = '<div class="wrap"> \
                    <iframe class="frame" \
                    srcdoc=\"%s\"></iframe></div>' % escaped_html

            html = html + frame

        html = html + '</body></html>'
        return html

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
        # get the notebook in the correct format (nbnode)
        current_nb = nbformat.from_dict(action_data['model'])

        # generate file names
        os_dir, fname = os.path.split(os_path)
        fname, file_ext = os.path.splitext(fname)
        dest_dir = os.path.join(volume, fname)
        version_dir = os.path.join(dest_dir, "versions")
        dbname = os.path.join(dest_dir, fname + ".db")
        dest_fname = os.path.join(dest_dir, fname + ".ipynb")
        date_string = datetime.datetime.now().strftime("-%Y-%m-%d-%H-%M-%S-%f")
        ver_fname = os.path.join(version_dir, fname + date_string + ".ipynb")

        # if needed, create storage directories on the external volume
        if not os.path.isdir(dest_dir):
            create_dir(dest_dir)
            create_dir(version_dir)

        # save information about the action to an sqlite database
        if track_actions:
            record_action_to_db(action_data, dest_fname, dbname)

        # save file versions and check for changes only if different from last notebook
        if os.path.isfile(dest_fname):
            cells_to_check = list(range(len(current_nb['cells']))) # check all cells
            diff = get_diff_at_indices(cells_to_check, action_data, dest_fname, True)
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
            verify_git_repository(dest_dir)
            git_commit(fname, dest_dir)

def was_saved_recently(version_dir, min_time=60):
    """ check if a previous version of the file has been saved recently

    version_dir: (str) dir to look for previous versions
    min_time: (int) minimum time in seconds allowed between saves """

    #TODO check for better way to get most recent file in dir, maybe using glob
    #TODO filter file list to only include .ipynb
    versions = [f for f in os.listdir(version_dir)
        if os.path.isfile(os.path.join(version_dir, f)) and f[-6:] == '.ipynb']
    if len(versions) > 0:
        vdir, vname = os.path.split(versions[-1])
        vname, vext = os.path.splitext(vname)
        last_time_saved = datetime.datetime.strptime(vname[-26:], "%Y-%m-%d-%H-%M-%S-%f")
        delta = (datetime.datetime.now() - last_time_saved).seconds
        return delta <= min_time
    else:
        return False

def create_dir(directory):
    try:
        os.makedirs(directory)
    except OSError:
        pass

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
