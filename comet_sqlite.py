"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

import pickle
import sqlite3

from comet_diff import get_diff_at_indices, indices_to_check

def record_action_to_db(action_data, dest_fname, db):
    """
    save action to sqlite database

    action_data: (dict) data about action, see above for more details
    dest_fname: (str) full path to where file is saved on volume
    db: (str) path to sqlite database
    """

    action = action_data['name']
    selected_index = action_data['index']
    selected_indices = action_data['indices']
    len_current = len(action_data['model']['cells'])

    check_indices = indices_to_check(action, selected_index, selected_indices,
                                    len_current)
    diff = get_diff_at_indices(check_indices, action_data, dest_fname, True)

    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS actions (time integer, name text,
                cell_index text, diff text)''') #id integer primary key autoincrement,
    tuple_action = (str(action_data['time']), action_data['name'],
                    str(action_data['index']), pickle.dumps(diff))
    c.execute('INSERT INTO actions VALUES (?,?,?,?)', tuple_action)
    conn.commit()
    conn.close()
