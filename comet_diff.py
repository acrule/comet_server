"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

import os
import nbformat

def get_diff_at_indices(indices, action_data, dest_fname,
                        compare_outputs = False):
    """
    look for diff at particular indices

    indices: (list) cell indices to compare
    action_data: (dict) new notebook data to compare
    dest_fname: (str) name of file to compare to
    compare_outputs: (bool) compare cell outputs
    """

    diff = {}

    # if there is no prior notebook to compare to, we cannot generate a diff
    if not os.path.isfile(dest_fname):
        return diff

    prior_nb = nbformat.read(dest_fname, nbformat.NO_CONVERT)['cells']
    current_nb = action_data['model']['cells']

    # Special case for undo-cell-deletion. The cell may insert at any part of
    # the notebook, so simply return the first cell that is not the same
    if action_data['name'] == 'undo-cell-deletion':
        for i in indices:
            if (prior_nb[i]["source"] != current_nb[i]["source"]
                or i >= len(prior_nb)): # its a new cell at the end of the nb
                    diff[i] = current_nb[i]
                    return diff

    # for all other action types
    for i in indices:
        # compare source
        if i >= len(prior_nb):
            diff[i] = current_nb[i]
        elif (prior_nb[i]["cell_type"] != current_nb[i]["cell_type"]
            or prior_nb[i]["source"] != current_nb[i]["source"]): # its a new cell at the end of the nb
                diff[i] = current_nb[i]
        # compare outputs
        elif compare_outputs and current_nb[i]["cell_type"] == "code":
            prior_outputs = prior_nb[i]['outputs']
            current_outputs = current_nb[i]['outputs']

            if len(prior_outputs) != len(current_outputs):
                diff[i] = current_nb[i]
            else:
                for j in range(len(current_outputs)):
                    # check that the output type matches
                    if prior_outputs[j]['output_type'] != current_outputs[j]['output_type']:
                        diff[i] = current_nb[i]
                    # and that the relevant data matches
                    elif ((prior_outputs[j]['output_type'] in ["display_data","execute_result"]
                        and prior_outputs[j]['data'] != current_outputs[j]['data'])
                        or (prior_outputs[j]['output_type'] == "stream"
                        and prior_outputs[j]['text'] != current_outputs[j]['text'])
                        or (prior_outputs[j]['output_type'] == "error"
                        and prior_outputs[j]['evalue'] != current_outputs[j]['evalue'])):
                            diff[i] = current_nb[i]
    return diff

def indices_to_check(action, selected_index, selected_indices, len_current):
    """
    Find what notebook cells to check for changes based on the type of action

    action: (str) action name
    selected_index: (int) single selected cell
    selected_indices: (list of ints) all selected cells
    len_current: (int) length in cells of the notebook we are comparing
    """

    if action in ['run-cell','insert-cell-above','paste-cell-above',
                'merge-cell-with-next-cell','change-cell-to-markdown',
                'change-cell-to-code','change-cell-to-raw','clear-cell-output',
                'toggle-cell-output-collapsed','toggle-cell-output-scrolled']:
        return [selected_index]
    elif action in ['insert-cell-below','paste-cell-below']:
        return [selected_index + 1]
    elif action in ['run-cell-and-insert-below','run-cell-and-select-next',
                    'split-cell-at-cursor','move-cell-down']:
        if selected_index >= len_current:
            return []
        elif selected_index == len_current-1:
            return [selected_index]
        else:
            return [selected_index, selected_index + 1]
    elif action in ['move-cell-up']:
        if selected_index == 0:
            return []
        else:
            return [selected_index, selected_index-1]
    elif action in ['run-all-cells','restart-kernel-and-clear-output']:
        return [x for x in range(len_current)]
    elif action in ['run-all-cells-above']:
        return [x for x in range(selected_index)]
    elif action in ['run-all-cells-below']:
        return [x for x in range(selected_index, len_current)]
    elif action in ['undo-cell-deletion']:
        return [x for x in range(0, len_current)]# scan all cells to look for 1st new cell
    elif action in ['merge-cell-with-previous-cell']:
        return [max([0, selected_index-1])]
    elif action in ['merge-selected-cells','merge-cells']:
        return min(selected_indices)
    else:
        return []