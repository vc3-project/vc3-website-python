# VC3 Website in Python/Flask Framework
Virtual Clusters for Community Computing project website using
the Globus [platform](https://www.globus.org/platform).

## Overview
This repository contains the server application for the VC3 project. To launch the application, run:

    python run_python.py

This should initiate the CherryPy server, which sits on top of a Flask micro-framework application. From here, Flask will properly render any requests for templates and Flatpages.

## Adding/Updating News Articles
For ease of navigation and organization, new .md files should follow the naming convention:

    YYYY-MM-DD-title-of-article.md

In order to add a new article, create a new markdown (.md) file within the /portal/pages directory.
You may manually create a new .md file within this directory or enter the command:

    touch /portal/pages/YYYY-MM-DD-title-of-article.md

Once the new article.md file is create, each markdown file is made up of a YAML mapping
of metadata, a blank line, and the page body:

    title: VC3 Kickoff Meeting
    date: June 7, 2016
    tags: [meetings]

    Hello, *World*!

    Lorem ipsum dolor sit amen, ...

Where the "title" and "date" refers to a title and date of your choosing to be displayed.
All tags must be nested within a bracketed-list and separated by commas:

    tags: [tag1, tag2, tag3, and, so, on]
