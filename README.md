# VC3 Website in Python/Flask Framework
Virtual Clusters for Community Computing project web application.

## Overview
This repository contains the portal application for the VC3 project.

The VC3 Website runs on a CherryPy WSGI server, which handles incoming http connections and relay connections to python code. The python code uses a Flask framework in order to handle incoming requests and generate appropriate pages, which are rendered as .jinja2 templates.

In order to setup this website within the VM, clone the vc3-deployment-infrastructure scripts from [here](https://github.com/vc3-project/vc3-deployment-infrastructure) and follow the readme. The respective scripts will clone and pull the latest vc3-website-python git repository, set up a virtual environment with the necessary dependencies for deployment, and start the server, such that it will continue running in the background until it has been manually killed.

The third script `update_pages_directory.sh` from the [vc3-deployment-infrastructure](https://github.com/vc3-project/vc3-deployment-infrastructure) will allow the Blog pages to automatically update and pull from a separate repository [here](https://github.com/vc3-project/vc3-flatpages). Markdown pages may be created following a YAML mapping of metadata, and generated to be automatically displayed on the VC3 website.
