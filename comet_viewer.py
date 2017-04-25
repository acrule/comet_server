"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

import os
import cgi
import nbconvert

def get_viewer_html(data_dir):
    html = '<html><head><style>\
            body{ width: 20000px;}\
            .wrap{ \
                width: 320px; height: 4000px;\
                padding: 0;\
                overflow: hidden;\
                float: left;}\
            .frame { width: 1280px;\
                height: 12000px;\
                border: 1px solid black}\
            .frame { \
                -moz-transform: scale(0.25); \
                -moz-transform-origin: 0 0; \
                -o-transform: scale(0.25); \
                -o-transform-origin: 0 0; \
                -webkit-transform: scale(0.25); \
                -webkit-transform-origin: 0 0;} \
            </style></head><body>'

    version_dir = os.path.join(data_dir, 'versions')

    if os.path.isdir(version_dir):
        versions = [f for f in os.listdir(version_dir)
            if os.path.isfile(os.path.join(version_dir, f))
            and f[-6:] == '.ipynb']

        for v in versions:
            nb_path = os.path.join(version_dir, v)
            html_exporter = nbconvert.HTMLExporter()
            (body, resources) = html_exporter.from_file(nb_path)
            escaped_html = cgi.escape(body, True)

            frame = '<div class="wrap"> \
                        <iframe class="frame" srcdoc=\"%s\">\
                        </iframe>\
                    </div>' % escaped_html
            html = html + frame

        html = html + '</body></html>'
    
    else:
        html = '<h1>No Data</h1> <p>There is no data saved for %s</p>' % path    
        
    return html
