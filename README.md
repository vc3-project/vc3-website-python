# VC3 Website in Python/Flask Framework
Virtual Clusters for Community Computing project website using
the Globus [platform](https://www.globus.org/platform).

## Overview
<<<<<<< HEAD
This repository contains the server application for the VC3 project. To launch the application, run:

    python run_python.py

This should initiate the CherryPy server, which sits on top of a Flask micro-framework application. From here, Flask will properly render any requests for templates and Flatpages.
=======
This repository contains the portal applications for the VC3 project.
>>>>>>> b334dbd2ef122f151987e360af69320ddfd637c3

The VC3 Website runs on a CherryPy WSGI server, which handles incoming http connections and relay connections to python code. The python code uses a Flask framework in order to handle incoming requests and generate appropriate pages, which are rendered as .jinja2 templates.

The News pages are pulled from a separate repository [here](https://github.com/vc3-project/vc3-flatpages). Markdown pages made be created following a YAML mapping of metadata, and generated to be automatically displayed on the VC3 website.
