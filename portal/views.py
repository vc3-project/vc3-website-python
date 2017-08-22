from flask import (abort, flash, redirect, render_template, request,
                   session, url_for, g)
import requests
import logging
import os

# from configparser import ConfigParser
# from vc3client.client import VC3ClientAPI

from vc3client import client
from ConfigParser import SafeConfigParser

try:
    from urllib.parse import urlencode
except:
    from urllib import urlencode

from globus_sdk import (TransferClient, TransferAPIError,
                        TransferData, RefreshTokenAuthorizer,
                        AuthClient, AccessTokenAuthorizer)


from portal import app, database, pages
from portal.decorators import authenticated
from portal.utils import (load_portal_client, get_portal_tokens,
                          get_safe_redirect)

c = SafeConfigParser()
c.readfp(open('/etc/vc3/vc3-client.conf'))
<<<<<<< HEAD
# c.readfp(open('/Users/JeremyVan/Documents/Programming/UChicago/VC3_Project/vc3-website-python/vc3-client/etc/vc3-client.conf'))
=======
#c.readfp(open('/Users/JeremyVan/Documents/Programming/UChicago/VC3_Project/vc3-website-python/vc3-client/etc/vc3-client.conf'))
>>>>>>> dfe5a531c88907392633ce90aa0f6da3577e5aa7
clientapi = client.VC3ClientAPI(c)


@app.route('/', methods=['GET'])
def home():
    """Home page - play with it if you must!"""
    return render_template('home.html')


@app.route('/status', methods=['GET', 'POST'])
def status():
    """Status page - to display System Operational Status"""
    return render_template('status.html')

# -----------------------------------------
# CURRENT blog PAGE AND ALL ARTICLE ROUTES
# -----------------------------------------


@app.route('/blog', methods=['GET'])
def blog():
    """Articles are pages with a publication date"""
    articles = (p for p in pages if 'date' in p.meta)
    """Show the 10 most recent articles, most recent first"""
    latest = sorted(articles, reverse=True, key=lambda p: p.meta['date'])
    """Send the user to the blog page"""
    return render_template('blog.html', pages=latest[:10])


@app.route('/blog/tag/<string:tag>/', methods=['GET'])
def tag(tag):
    """Automatic routing and compiling for article tags"""
    tagged = [p for p in pages if tag in p.meta.get('tags', [])]
    return render_template('blog_tag.html', pages=tagged, tag=tag)


@app.route('/blog/<path:path>/', methods=['GET'])
def page(path):
    """Automatic routing and generates markdown flatpages in /pages directory"""
    page = pages.get_or_404(path)
    return render_template('blog_page.html', page=page)


@app.route('/community', methods=['GET'])
def community():
    """Send the user to community page"""
    return render_template('community.html')


@app.route('/documentations', methods=['GET'])
def documentations():
    """Send the user to documentations page"""
    return render_template('documentations.html')


@app.route('/team', methods=['GET'])
def team():
    """Send the user to team page"""
    return render_template('team.html')


@app.route('/signup', methods=['GET'])
def signup():
    """Send the user to Globus Auth with signup=1."""
    return redirect(url_for('authcallback', signup=1))


@app.route('/login', methods=['GET'])
def login():
    """Send the user to Globus Auth."""
    return redirect(url_for('authcallback'))


@app.route('/logout', methods=['GET'])
@authenticated
def logout():
    """
    - Revoke the tokens with Globus Auth.
    - Destroy the session state.
    - Redirect the user to the Globus Auth logout page.
    """
    globusclient = load_portal_client()

    # Revoke the tokens with Globus Auth
    for token, token_type in (
            (token_info[ty], ty)
            # get all of the token info dicts
            for token_info in session['tokens'].values()
            # cross product with the set of token types
            for ty in ('access_token', 'refresh_token')
            # only where the relevant token is actually present
            if token_info[ty] is not None):
        globusclient.oauth2_revoke_token(
            token, additional_params={'token_type_hint': token_type})

    # Destroy the session state
    session.clear()

    redirect_uri = url_for('home', _external=True)

    ga_logout_url = []
    ga_logout_url.append(app.config['GLOBUS_AUTH_LOGOUT_URI'])
    ga_logout_url.append('?client={}'.format(app.config['PORTAL_CLIENT_ID']))
    ga_logout_url.append('&redirect_uri={}'.format(redirect_uri))
    ga_logout_url.append('&redirect_name=Globus Sample Data Portal')

    # Redirect the user to the Globus Auth logout page
    # return redirect(''.join(ga_logout_url))
    return redirect(url_for('home'))


@app.route('/profile', methods=['GET', 'POST'])
@authenticated
def profile():
    """User profile information. Assocated with a Globus Auth identity."""
    #c = SafeConfigParser()
    # c.readfp(open(
    #    '/etc/vc3/vc3-client.conf'))
    #clientapi = client.VC3ClientAPI(c)

    if request.method == 'GET':
        # identity_id = session.get('primary_identity')
        # profile = database.load_profile(identity_id)
        userlist = clientapi.listUsers()
        profile = None

        for user in userlist:
            if session['primary_identity'] == user.identity_id:
                profile = user

        if profile:

            session['name'] = profile.name
            session['first'] = profile.first
            session['last'] = profile.last
            session['email'] = profile.email
            session['institution'] = profile.institution
            session['primary_identity'] = profile.identity_id
        else:
            flash(
                'Please complete any missing profile fields and press Save.')

        if request.args.get('next'):
            session['next'] = get_safe_redirect()

        return render_template('profile.html')
    elif request.method == 'POST':
        name = session['name'] = request.form['name']
        first = session['first'] = request.form['first']
        last = session['last'] = request.form['last']
        email = session['email'] = request.form['email']
        institution = session['institution'] = request.form['institution']
        identity_id = session['primary_identity']

        # print identity_id

        newuser = clientapi.defineUser(identity_id=identity_id,
                                       name=name,
                                       first=first,
                                       last=last,
                                       email=email,
                                       institution=institution)

        # print(newuser)
        clientapi.storeUser(newuser)

        flash('Thank you! Your profile has been successfully updated.')

        if 'next' in session:
            redirect_to = session['next']
            session.pop('next')
        else:
            redirect_to = url_for('profile')

        return redirect(redirect_to)


@app.route('/authcallback', methods=['GET'])
def authcallback():
    """Handles the interaction with Globus Auth."""
    # If we're coming back from Globus Auth in an error state, the error
    # will be in the "error" query string parameter.

    if 'error' in request.args:
        flash("You could not be logged into the portal: " +
              request.args.get('error_description', request.args['error']))
        return redirect(url_for('home'))

    # Set up our Globus Auth/OAuth2 state
    redirect_uri = url_for('authcallback', _external=True)

    globusclient = load_portal_client()
    globusclient.oauth2_start_flow(redirect_uri, refresh_tokens=True)

    # If there's no "code" query string parameter, we're in this route
    # starting a Globus Auth login flow.
    if 'code' not in request.args:

        additional_authorize_params = (
            {'signup': 1} if request.args.get('signup') else {})

        auth_uri = globusclient.oauth2_get_authorize_url(
            additional_params=additional_authorize_params)

        return redirect(auth_uri)
    else:
        # If we do have a "code" param, we're coming back from Globus Auth
        # and can start the process of exchanging an auth code for a token.
        code = request.args.get('code')
        tokens = globusclient.oauth2_exchange_code_for_tokens(code)

        id_token = tokens.decode_id_token(globusclient)
        session.update(
            tokens=tokens.by_resource_server,
            is_authenticated=True,
            name=id_token.get('name', ''),
            email=id_token.get('email', ''),
            institution=id_token.get('institution', ''),
            primary_username=id_token.get('preferred_username'),
            primary_identity=id_token.get('sub'),
        )

        # print(session)
        userlist = clientapi.listUsers()
        profile = None

        for user in userlist:
            if session['primary_identity'] == user.identity_id:
                profile = user

        if profile:

            session['name'] = profile.name
            session['first'] = profile.first
            session['last'] = profile.last
            session['email'] = profile.email
            session['institution'] = profile.institution
            session['primary_identity'] = profile.identity_id
        else:
            return redirect(url_for('profile',
                                    next=url_for('home')))

        return redirect(url_for('profile'))


# -----------------------------------------
# CURRENT PROJECT PAGE AND ALL PROJECT ROUTES
# -----------------------------------------


@app.route('/new', methods=['GET', 'POST'])
@authenticated
def new():
    return render_template('new.html')


@app.route('/project', methods=['GET', 'POST'])
@authenticated
def project():

    if request.method == 'POST':
        name = request.form['name']
        owner = request.form['owner']
        members = request.form['members'].split(",")

        newproject = clientapi.defineProject(name=name, owner=owner, members=members)
        clientapi.storeProject(newproject)

        return render_template('project.html')
    elif request.method == 'GET':
        identity_id = session['primary_identity']
        # projects = clientapi.getProjectsOfUser(username=identity_id)
        projects = clientapi.listProjects()
        # for project in projects:
        #     print(project)
        return render_template('project.html', projects=projects)


@app.route('/project/<name>', methods=['GET', 'POST'])
@authenticated
def project_name(name):
    projects = clientapi.listProjects()
    allocations = clientapi.listAllocations()
    projectname = name

    if request.method == 'GET':
        for project in projects:
            if project.name == name:
                name = project.name
                owner = project.owner
                members = project.members
        return render_template('projects_pages.html', name=name, owner=owner, members=members, project=project, allocations=allocations, projects=projects)

    elif request.method == 'POST':
        allocation = request.form['allocation']
        clientapi.addAllocationToProject(allocation, projectname)

        return render_template('projects_pages.html')


@app.route('/cluster', methods=['GET', 'POST'])
@authenticated
def cluster():

    # if request.method == 'POST':
    #     name = request.form['name']
    #     owner = request.form['owner']
    #     nodesets = request.form['nodesets']
    #
    #     newcluster = clientapi.defineCluster(
    #         name=name, owner=owner, nodesets=nodesets)
    #     clientapi.storeCluster(newcluster)
    #
    #     return render_template('cluster.html')
    # elif request.method == 'GET':
    #     clusters = clientapi.listClusters()
    #
    #     return render_template('cluster.html', clusters=clusters)
    return render_template('cluster.html')


@app.route('/allocation', methods=['GET', 'POST'])
@authenticated
def allocation():

    if request.method == 'POST':
        name = request.form['name']
        owner = request.form['owner']
        resource = request.form['resource']
        accountname = request.form['accountname']

        newallocation = clientapi.defineAllocation(
            name=name, owner=owner, resource=resource, accountname=accountname)
        clientapi.storeAllocation(newallocation)

        return render_template('allocation.html')
    elif request.method == 'GET':
        allocations = clientapi.listAllocations()
        resources = clientapi.listResources()
        return render_template('allocation.html', allocations=allocations, resources=resources)
    return render_template('allocation.html', allocations=allocations, resources=resources)


@app.route('/allocation/new', methods=['GET', 'POST'])
@authenticated
def new_allocation():
    if request.method == 'POST':
        name = request.form['name']
        owner = request.form['owner']
        resource = request.form['resource']
        accountname = request.form['accountname']

        newallocation = clientapi.defineAllocation(
            name=name, owner=owner, resource=resource, accountname=accountname)
        clientapi.storeAllocation(newallocation)

        return render_template('allocation.html')
    elif request.method == 'GET':
        resources = clientapi.listResources()
        for resource in resources:
            resourcename = resource.name
        print resourcename
        return render_template('new_allocation.html', resources=resources, name=resourcename)
    return render_template('new_allocation.html')


@app.route('/resource', methods=['GET', 'POST'])
@authenticated
def resource():

    if request.method == 'GET':
        resources = clientapi.listResources()
    return render_template('resource.html', resources=resources)


@app.route('/resource/<name>', methods=['GET', 'POST'])
@authenticated
def resource_name(name):
    resources = clientapi.listResources()

    if request.method == 'GET':
        for resource in resources:
            if resource.name == name:
                resourcename = resource.name
                owner = resource.owner
                accesstype = resource.accesstype
                accessmethod = resource.accessmethod
                accessflavor = resource.accessflavor
                accesshost = resource.accesshost
                accessport = resource.accessport
                gridresource = resource.gridresource

    return render_template('resource_profile.html', name=resourcename, owner=owner,
    accesstype=accesstype, accessmethod=accessmethod, accessflavor=accessflavor,
    accesshost=accesshost, accessport=accessport, gridresource=gridresource, resource=resource)


@app.route('/dashboard', methods=['GET', 'POST'])
@authenticated
def dashboard():
    return render_template('dashboard.html')
