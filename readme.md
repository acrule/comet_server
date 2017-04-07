# Comet
Comet is a Jupyter Notebook server extension that tracks changes to the notebook over time. It works in tandem with the [Comet notebook extension](https://github.com/activityhistory/comet). You must have both the server and notebook extension installed for the tracking to work properly since the notebook extension listens for events and send information to the server for processing.  

## What Comet Tracks
Comet tracks how your notebook changes over time. It does so by:
1. tracking actions such as creating, deleting, moving, or executing cells
2. tracking how your notebook changes as a result of these actions

Comet tracks this information in three ways:
1. committing every notebook change to a local git repository
2. periodically saving a full version of the notebook
3. saving the name and time of every action to an sqlite database

## Installation
Comet is a research tool designed to help scientists in human-computer interaction better understand how Jupyter Notebooks  evolve over time. It is primarily a recording tool with very limited support for visualizing or reviewing the recorded data.

Comet expects all data to be saved to an external drive (e.g. a USB key) and will not run unless it detects a mounted drive with a config file named `traces.cfg`.

The Comet server extension may be installed by downloading the `comet_server.py` file and placing it anywhere on your python path. We recommend saving it to the `site-packages` folder of your python distribution, such as `/anaconda/lib/python3.5/site-packages`. We will work on making this package pip installable in the future to ease installation.

You will also need to change your `jupyter_notebook_config.py` file to tell Jupyter to run the extension. Typically this file resides ina folder called `.jupyter` on your home directory. You can reach this file by opening your terminal and typing:

```
open ~/.jupyter
```

If you do not see the file there, you can generate one by running the following command:

```
jupyter notebook --generate-config
```

Once you have the file, insert the following lines.

```
c = get_config()
c.NotebookApp.nbserver_extensions = {'comet_server.comet_server':True}

```

See the [Comet repo](https://github.com/activityhistory/comet) for instructions on how to install the frontend notebook extension.
