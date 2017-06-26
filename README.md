# VC3 Website in Python/Flask Framework
Virtual Clusters for Community Computing project web application.

## Overview
This repository contains the portal application for the VC3 project.

The VC3 Website runs on a CherryPy WSGI server, which handles incoming http connections and relay connections to python code. The python code uses a Flask framework in order to handle incoming requests and generate appropriate pages, which are rendered as .jinja2 templates.

The News pages are pulled from a separate repository [here](https://github.com/vc3-project/vc3-flatpages). Markdown pages made be created following a YAML mapping of metadata, and generated to be automatically displayed on the VC3 website.

# vc3-client
Command-line client utility and associated libraries.

# vc3-info-service
Daemon framework for deploying the information service

Notes: CherryPy Version 3.2.2 required, otherwise SSL doesn't work.

Source RPM (rebuildable for RHEL6,7 and Fedora) here:
  http://dev.racf.bnl.gov/dist/vc3/

Do rpmbuild --rebuild python-cherrypy-3.2.2-4.el7.src.rpm
