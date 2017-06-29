# VC3 Website in Python/Flask Framework
Virtual Clusters for Community Computing project web application.

## Overview
This repository contains the portal application for the VC3 project.

The VC3 Website runs on a CherryPy WSGI server, which handles incoming http connections and relay connections to python code. The python code uses a Flask framework in order to handle incoming requests and generate appropriate pages, which are rendered as .jinja2 templates.

## Deployment Infrastructure
In order to setup this website within the VM, clone the vc3-deployment-infrastructure scripts from [here](https://github.com/vc3-project/vc3-deployment-infrastructure) and follow the readme. The respective scripts will clone and pull the latest vc3-website-python git repository, set up a virtual environment with the necessary dependencies for deployment, and start the server, such that it will continue running in the background until it has been manually killed.

## Blog Flat-Pages Integration
The third script `update_pages_directory.sh` from the [vc3-deployment-infrastructure](https://github.com/vc3-project/vc3-deployment-infrastructure) will allow the Blog pages to automatically update and pull from a separate repository [here](https://github.com/vc3-project/vc3-flatpages). Markdown pages may be created following a YAML mapping of metadata, and generated to be automatically displayed on the VC3 website.

## Creating New Routes
All website routes are located in `portal/views.py` and typically render .jinja2 templates pages. In order to create a new route, follow the basic notation:


```@app.route('/new-route', methods=['GET', 'POST'])
def new-route():
    """Send the user to new-route page"""
    return render_template('new-route.jinja2')
```

In order for the route to render the .jinja2 template, you must create a new .jinja2 page within the `portal/templates` directory.

Below is a suggested starting template for new .jinja2 pages for development of the website landing view (what users see when they are not logged in):

```{%extends "base.jinja2"%}

{%block title%}New Route Name{%endblock%}

{%block body%}

<!--==========================
  New Route Section
============================-->

<section id="new-route">

  <div class="container wow fadeInUp">

    <div class="row">

      Enter code and content here

    </div>

  </div>

</section>

{endblock}
```

Below is a suggested starting template for new .jinja2 pages for development of the website's logged in view (what users see when they ARE logged in):

```{%extends "loginbase.jinja2"%}

{%block title%}New Route/Page Name{%endblock%}

{%block body%}

<!--==========================
  New Route Section
============================-->

<div class="content container">

  <div class="container-fluid">

    <div class="row">

      Enter code and content here

    </div>

  </div>

</div>

{endblock}
```
