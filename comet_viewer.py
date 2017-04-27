"""
Comet Server: Server extension paired with nbextension to track notebook use
"""

import os
import cgi
import datetime
import nbconvert
import nbformat

from comet_sqlite import get_viewer_data

def get_viewer_html(data_dir):
                
    version_dir = os.path.join(data_dir, 'versions')
    filename = data_dir.split('/')[-1]
    db = os.path.join(data_dir, filename + ".db")
    
    numDeletions, numRuns, totalTime = get_viewer_data(db)
    
    if os.path.isdir(version_dir):            
        data = {'name': filename,
                'editTime': totalTime,
                'numRuns': numRuns,
                'numDeletions': numDeletions,
                'versions':[]};
        
        versions = [f for f in os.listdir(version_dir)
            if os.path.isfile(os.path.join(version_dir, f))
            and f[-6:] == '.ipynb']

        for i, v in enumerate(versions):
            
            version_data = {'num': i,
                            'time': v[-26:],
                            'cells':[]};
                        
            nb_path = os.path.join(version_dir, v)
            nb_cells = nbformat.read(nb_path, nbformat.NO_CONVERT)['cells']
            
            # cells can have multiple outputs , each with a different type
            # here we track the "highest" level output with 
            # error> display_data > execute result > stream
            for c in nb_cells:
                cell_type = c.cell_type
                if c.cell_type == "code":
                    output_types = [x.output_type for x in c.outputs]
                    if "error" in output_types:
                        cell_type = "error"
                    elif "display_data" in output_types:
                        cell_type = "display_data"
                    elif "execute_result" in output_types:
                        cell_type = "execute_result"
                    elif "stream" in output_types:
                        cell_type = "stream"
                
                version_data['cells'].append(cell_type)
            data['versions'].append(version_data)        
        
        html = """<!DOCTYPE html>\n
            <html>\n
            <style>\n
            body{\n
                width: 960px;\n
                margin: auto;\n
                font-family: "Helvetica Neue", Helvetica, sans-serif;
                color: #333;
            }\n
            \n
            .stat{
                width: 240px;
                float: left;
            }
            </style>\n
            <body>\n
            <script src="https://d3js.org/d3.v4.min.js"></script>\n
            <script>\n
            var width = 960;\n
            var height = 600;\n
            var cellSize = 16;\n
            \n
            var data = """ + str(data) + """\n
            \n
            var title = d3.select("body")\n
                .append("h1")\n
                .text(data.name);\n
            \n
            d3.select("body")\n
                .append("hr")\n
            \n
            var time = d3.select("body")\n
                .append("div")\n
                .attr("class", "stat")\n
                    .append("h2")\n
                    .text(function(){\n
                        hours = Math.floor( data.editTime / 3600 );\n
                        minutes = Math.floor( ( data.editTime - hours * 3600 ) / 60 );\n
                        text = hours.toString() + "h " + minutes.toString() + "m editing";\n
                        return text;\n
                })\n
            \n
            var runs = d3.select("body")\n
                .append("div")\n
                .attr("class", "stat")\n
                    .append("h2")\n
                    .text(function(){\n
                        text = data.numRuns.toString() + " cells run";\n
                        return text;\n
                })\n
            \n
            var deletions = d3.select("body")\n
                .append("div")\n
                .attr("class", "stat")\n
                    .append("h2")\n
                    .text(function(){\n
                        text = data.numDeletions.toString() + " cells deleted";\n
                        return text;\n
                })\n
            \n    
            var versions = d3.select("body")\n
                .append("div")\n
                .attr("class", "stat")\n
                    .append("h2")\n
                    .text(function(){\n
                        text = data.versions.length.toString() + " versions";\n
                        return text;\n
                })\n
            \n
            var svg = d3.select("body")\n
                .append("svg")\n
                .attr("width", width)\n
                .attr("height", height)\n
            \n
            var nb = svg.selectAll("g")\n
                .data(data.versions)\n
                .enter().append("g")\n
            \n
            nb.each(function(p, j) {\n
                d3.select(this)\n
                .selectAll("rect")\n
                    .data(function(d){return d.cells; })\n
                    .enter().append("rect")\n
                    .attr("width", cellSize)\n
                    .attr("height", cellSize)\n
                    .attr("x", function(d, i){ return (j-1)*cellSize; })\n
                    .attr("y", function(d, i) { return i * cellSize; })\n
                    .attr("fill", function(d) { 
                        type_colors = {
                            "markdown": "#82b446",
                            "code": "silver",
                            "error": "#b44682",
                            "stream": "grey",
                            "execute_result": "grey",
                            "display_data": "steelblue"
                        }
                        return type_colors[d]
                     })\n
                    .attr("stroke", "white");\n
            });\n
            \n
            </script>\n
            </body>\n
            </html>"""  
    
    else:
        html = """<!DOCTYPE html>\n
            <html>\n
            <style>\n
            body{\n
                width: 960px;\n
                margin: auto;\n
                font-family: "Helvetica Neue", Helvetica, sans-serif;
                color: #333;
            }\n
            </style>\n
            <body>\n
            <h1>No Data</h1> 
            <hr>
            <p>There is no Comet data saved for <i>%s</i></p>
            </body>
            </html>
            """ % data_dir.split('/')[-1]
        
    return html
