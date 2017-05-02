"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

import os
import time
import pickle
import sqlite3
import nbformat

from comet_diff import get_diff_at_indices, indices_to_check

def get_viewer_data(db):

    conn = sqlite3.connect(db)
    c = conn.cursor()
    
    c.execute("SELECT name FROM actions WHERE name = 'delete-cell' ")
    rows = c.fetchall()
    num_deletions = len(rows)
    
    # TODO how to count when multiple cells are selected and run, or run-all?
    c.execute("SELECT name FROM actions WHERE name LIKE  'run-cell%' ")
    rows = c.fetchall()
    num_runs = len(rows)
    
    # TODO only need to selelct times
    c.execute("SELECT time FROM actions")
    rows = c.fetchall()
    total_time = 0;
    start_time = rows[0][0]
    last_time = rows[0][0]
    for i in range(1,len(rows)):
        # 5 minutes
        if (rows[i][0] - last_time) >= (5 * 60 * 1000) or i == len(rows) - 1:
            total_time = total_time + last_time - start_time            
            start_time = rows[i][0]
            last_time = rows[i][0]
        else:
            last_time = rows[i][0]
            
    
    return (num_deletions, num_runs, total_time/1000)

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
    
    if action_data['name'] in ['unselect-cell'] and diff == {}: 
        return

    # save the data to the database
    start_time = time.time()                
    conn = sqlite3.connect(db)
    conn_time = time.time()                
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS actions (time integer, name text,
                cell_index integer, selected_cells text, diff text)''') #id integer primary key autoincrement,
    table_time = time.time()                
    tuple_action = (str(action_data['time']), action_data['name'],
                    str(action_data['index']), str(action_data['indices']),
                    pickle.dumps(diff))
    c.execute('INSERT INTO actions VALUES (?,?,?,?,?)', tuple_action)
    insert_time = time.time()
    conn.commit()
    commit_time = time.time()
    conn.close()
    end_time = time.time()
    
    # print(action_data['name'])
    # print(end_time - commit_time)
    # print(commit_time - insert_time)
    # print(insert_time - table_time)
    # print(table_time - conn_time)
    # print(conn_time - start_time)
    # print(end_time - start_time)
    # print()
    
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
