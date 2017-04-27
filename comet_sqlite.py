"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

import os
import pickle
import sqlite3
import nbformat

from comet_diff import get_diff_at_indices, indices_to_check

def record_action_to_db(action_data, dest_fname, db):
    """
    save action to sqlite database

    action_data: (dict) data about action, see above for more details
    dest_fname: (str) full path to where file is saved on volume
    db: (str) path to sqlite database
    """    

    # handle edge cases of copy-cell and undo-cell-deletion events
    diff = get_action_diff(action_data, dest_fname)

    # track when cells are edited but not executed and another cell clicked
    if action_data['name'] in ['unselect-cell']:
        print(action_data['index'])
        print(diff)
    
    if action_data['name'] in ['unselect-cell'] and diff == {}: 
        return

    # save the data to the database
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS actions (time integer, name text,
                cell_index integer, selected_cells text, diff text)''') #id integer primary key autoincrement,
    tuple_action = (str(action_data['time']), action_data['name'],
                    str(action_data['index']), str(action_data['indices']),
                    pickle.dumps(diff))
    c.execute('INSERT INTO actions VALUES (?,?,?,?,?)', tuple_action)
    conn.commit()
    conn.close()
    
def get_action_diff(action_data, dest_fname):
    if not os.path.isfile(dest_fname):
        return {}
    
    diff = {} 
    action = action_data['name']
    selected_index = action_data['index']
    selected_indices = action_data['indices']
    current_nb = action_data['model']['cells']
    len_current = len(current_nb)
    prior_nb = nbformat.read(dest_fname, nbformat.NO_CONVERT)['cells']
    len_prior = len(prior_nb)
    
    check_indices = indices_to_check(action, selected_index, selected_indices,
                                    len_current, len_prior)

    # if it is a cut or copy action, save the copied cells as the diff
    if action in ['cut-cell', 'copy-cell', 'paste-cell-above', 
                'paste-cell-below', 'paste-cell-replace']:
        for i in check_indices:
            diff[i] = current_nb[i]

    # Special case for undo-cell-deletion. The cell may insert at any part of
    # the notebook, so simply return the first cell that is not the same
    elif action in ['undo-cell-deletion']:
        num_inserted = len_current - len_prior        
        if num_inserted > 0:
            first_diff = 0
            for i in range(len_current):
                if (prior_nb[i]["source"] != current_nb[i]["source"]
                    or i >= len(prior_nb)): # its a new cell at the end of the nb
                    first_diff = i
                    break
            for j in range(first_diff, first_diff + num_inserted):
                if j < len_current:
                    diff[j] = current_nb[j]
                    
    else:
        diff = get_diff_at_indices(check_indices, action_data, dest_fname, True)

    return diff
