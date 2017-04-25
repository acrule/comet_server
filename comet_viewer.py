"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

import os
import cgi
import nbconvert
import nbformat

def get_viewer_html(data_dir):
    
    data = []
    version_dir = os.path.join(data_dir, 'versions')
    
    if os.path.isdir(version_dir):
        versions = [f for f in os.listdir(version_dir)
            if os.path.isfile(os.path.join(version_dir, f))
            and f[-6:] == '.ipynb']

        for v in versions:
            nb_path = os.path.join(version_dir, v)
            nb_cells = nbformat.read(nb_path, nbformat.NO_CONVERT)['cells']
            cell_types = []
            for c in nb_cells:
                cell_types.append(c.cell_type)
            data.append(cell_types)
        
        html = """<!DOCTYPE html>\n
            <html>\n
            <body>\n
            <script src="https://d3js.org/d3.v4.min.js"></script>\n
            <script>\n
            var width = 960;\n
            var height = 600;\n
            var cellSize = 16;\n
            \n
            var data = """ + str(data) + """\n
            \n
            var svg = d3.select("body")\n
                .append("svg")\n
                .attr("width", width)\n
                .attr("height", height)\n
            \n
            var nb = svg.selectAll("g")\n
                .data(data)\n
                .enter().append("g")\n
            \n
            nb.each(function(p, j) {\n
                d3.select(this)\n
                .selectAll("rect")\n
                    .data(function(d){return d; })\n
                    .enter().append("rect")\n
                    .attr("width", cellSize)\n
                    .attr("height", cellSize)\n
                    .attr("x", function(d, i){ return j*cellSize; })\n
                    .attr("y", function(d, i) { return i * cellSize; })\n
                    .attr("fill", function(d) { if(d == "markdown"){return "steelblue";} else{return "gray"} })\n
                    .attr("stroke", "white");\n
            });\n
            \n
            </script>\n
            </body>\n
            </html>"""  
    
    else:
        html = '<h1>No Data</h1> <p>There is no data saved for %s</p>' % data_dir    
        
    return html
