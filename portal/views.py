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

from globus_sdk import (TransferData, RefreshTokenAuthorizer,
                        AuthClient, AccessTokenAuthorizer)


from portal import app, pages
from portal.decorators import authenticated
from portal.utils import (load_portal_client, get_portal_tokens,
                          get_safe_redirect)

c = SafeConfigParser()
c.readfp(open('/etc/vc3/vc3-client.conf'))

clientapi = client.VC3ClientAPI(c)
users = clientapi.listUsers()
allocations = clientapi.listAllocations()
clusters = clientapi.listClusters()
projects = clientapi.listProjects()
resources = clientapi.listResources()
vc3requests = clientapi.listRequests()


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

    if request.method == 'GET':
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
                'Please complete any missing profile fields before launching a cluster.')

        if request.args.get('next'):
            session['next'] = get_safe_redirect()

        return render_template('profile.html', users=userlist, allocations=allocations, clusters=clusters,
                               projects=projects, resources=resources, vc3requests=vc3requests)
    elif request.method == 'POST':
        name = session['name']
        # have name = session['primary_username'] =
        # request.form['primary_username'] no spaces or capitals?
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


@app.route('/profile/edit', methods=['GET', 'POST'])
@authenticated
def edit():
    return render_template('profile_edit.html')


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
    if request.method == 'GET':
        users = clientapi.listUsers()
        return render_template('new.html', users=users)

    elif request.method == 'POST':
        name = request.form['name']
        owner = session['name']
        members = request.form['members'].split(",")

        newproject = clientapi.defineProject(name=name, owner=owner, members=members)
        clientapi.storeProject(newproject)

        flash('Your project has been successfully created!')

        return redirect(url_for('project'))


@app.route('/project', methods=['GET', 'POST'])
@authenticated
def project():
    projects = clientapi.listProjects()

    if request.method == 'GET':
        return render_template('project.html', projects=projects)


@app.route('/project/<name>', methods=['GET', 'POST'])
@authenticated
def project_name(name):
    projects = clientapi.listProjects()
    allocations = clientapi.listAllocations()
    users = clientapi.listUsers()

    if request.method == 'GET':
        for project in projects:
            if project.name == name:
                name = project.name
                owner = project.owner
                members = project.members
        return render_template('projects_pages.html', name=name, owner=owner, members=members, allocations=allocations, projects=projects, users=users)


@app.route('/project/<name>/addmember', methods=['POST'])
@authenticated
def add_member(name):
    projects = clientapi.listProjects()

    if request.method == 'POST':
        user = request.form['newuser']

        for project in projects:
            if project.name == name:
                name = project.name
                owner = project.owner
                clientapi.addUserToProject(project=name, user=user)
                members = project.members

        flash('Successfully added member to project!')

        return redirect(url_for('project_name', name=name))


@app.route('/project/<name>/addallocation', methods=['POST'])
@authenticated
def add_allocation(name):
    projects = clientapi.listProjects()

    if request.method == 'POST':
        addallocation = request.form['allocation']

        for project in projects:
            if project.name == name:
                name = project.name
                clientapi.addAllocationToProject(allocation=addallocation, projectname=name)

        flash('Successfully added allocation to project!')

        return redirect(url_for('project_name', name=name))


@app.route('/cluster/new', methods=['GET', 'POST'])
@authenticated
def cluster_new():
    clusters = clientapi.listClusters()
    projects = clientapi.listProjects()
    nodesets = clientapi.listNodesets()

    if request.method == 'GET':
        return render_template('cluster_new.html')

    elif request.method == 'POST':
        name = request.form['name']
        owner = session['name']
        node_number = request.form['node_number']
        app_type = request.form['app_type']
        app_role = "worker-nodes"
        environment = "lincolnb-en1"

        nodeset = clientapi.defineNodeset(
            name=name, owner=owner, node_number=node_number, app_type=app_type, app_role=app_role, environment=environment)
        clientapi.storeNodeset(nodeset)
        # nodesets = clientapi.listNodesets()
        newcluster = clientapi.defineCluster(name=name, owner=owner)
        clientapi.storeCluster(newcluster)
        clientapi.addNodesetToCluster(nodesetname=nodeset.name, clustername=newcluster.name)

        flash('Your cluster template has been successfully defined!')
        return redirect(url_for('cluster'))


@app.route('/cluster', methods=['GET', 'POST'])
@authenticated
def cluster():
    clusters = clientapi.listClusters()
    projects = clientapi.listProjects()
    nodesets = clientapi.listNodesets()

    if request.method == 'GET':
        return render_template('cluster.html', clusters=clusters, projects=projects, nodesets=nodesets)


@app.route('/cluster/<name>', methods=['GET', 'POST'])
@authenticated
def cluster_name(name):
    clusters = clientapi.listClusters()
    projects = clientapi.listProjects()
    nodesets = clientapi.listNodesets()

    if request.method == 'GET':
        for cluster in clusters:
            if cluster.name == name:
                clustername = cluster.name
                owner = cluster.owner
                state = cluster.state

        return render_template('cluster_profile.html', name=clustername, owner=owner, state=state, nodesets=nodesets)

    elif request.method == 'POST':
        node_number = request.form['node_number']
        app_type = request.form['app_type']

        for cluster in clusters:
            if cluster.name == name:
                clustername = cluster.name
                owner = cluster.owner
                app_role = "worker-nodes"
                environment = "lincolnb-en1"

        nodeset = clientapi.defineNodeset(
            name=clustername, owner=owner, node_number=node_number, app_type=app_type, app_role=app_role, environment=environment)
        clientapi.storeNodeset(nodeset)
        newcluster = clientapi.defineCluster(name=clustername, owner=owner)
        clientapi.storeCluster(newcluster)
        clientapi.addNodesetToCluster(nodesetname=nodeset.name, clustername=newcluster.name)

        return render_template('cluster_profile.html', name=clustername, owner=owner, clusters=clusters, projects=projects)


@app.route('/cluster/edit/<name>', methods=['GET', 'POST'])
@authenticated
def cluster_edit(name):
    clusters = clientapi.listClusters()
    projects = clientapi.listProjects()

    if request.method == 'GET':
        for cluster in clusters:
            if cluster.name == name:
                clustername = cluster.name
                owner = cluster.owner
                nodesets = cluster.nodesets
                state = cluster.state
                acl = cluster.acl

        return render_template('cluster_edit.html', name=clustername, owner=owner, nodesets=nodesets, state=state, acl=acl)


@app.route('/allocation', methods=['GET', 'POST'])
@authenticated
def allocation():
    allocations = clientapi.listAllocations()
    resources = clientapi.listResources()
    projects = clientapi.listProjects()
    users = clientapi.listUsers()

    if request.method == 'GET':
        return render_template('allocation.html', allocations=allocations, resources=resources, users=users, projects=projects)


@app.route('/allocation/new', methods=['GET', 'POST'])
@authenticated
def new_allocation():
    if request.method == 'GET':
        resources = clientapi.listResources()
        for resource in resources:
            resourcename = resource.name
        return render_template('allocation_new.html', resources=resources, name=resourcename)

    elif request.method == 'POST':
        name = request.form['name']
        owner = session['name']
        resource = request.form['resource']
        accountname = request.form['accountname']

        newallocation = clientapi.defineAllocation(
            name=name, owner=owner, resource=resource, accountname=accountname)
        clientapi.storeAllocation(newallocation)

        flash('Your allocation has been successfully defined!')

        return redirect(url_for('allocation'))


@app.route('/allocation/<name>', methods=['GET', 'POST'])
@authenticated
def allocation_name(name):
    allocations = clientapi.listAllocations()
    resources = clientapi.listResources()
    projects = clientapi.listProjects()
    users = clientapi.listUsers()

    if request.method == 'GET':
        for allocation in allocations:
            if allocation.name == name:
                allocationname = allocation.name
                owner = allocation.owner
                resource = allocation.resource
                accountname = allocation.accountname
                pubtoken = allocation.pubtoken

        return render_template('allocation_profile.html', name=allocationname, owner=owner, resource=resource, accountname=accountname, pubtoken=pubtoken)

    elif request.method == 'POST':

        for allocation in allocations:
            if allocation.name == name:
                allocationname = allocation.name
                owner = allocation.owner
                resource = request.form['resource']
                accountname = request.form['accountname']
                pubtoken = allocation.pubtoken

        newallocation = clientapi.defineAllocation(
            name=allocationname, owner=owner, resource=resource, accountname=accountname)
        clientapi.storeAllocation(newallocation)

        return render_template('allocation_profile.html', name=allocationname, owner=owner, accountname=accountname, resource=resource, allocations=allocations, resources=resources)


@app.route('/allocation/edit/<name>', methods=['GET', 'POST'])
@authenticated
def allocation_edit(name):
    allocations = clientapi.listAllocations()
    resources = clientapi.listResources()

    if request.method == 'GET':
        for allocation in allocations:
            if allocation.name == name:
                allocationname = allocation.name
                owner = allocation.owner
                resource = allocation.resource
                accountname = allocation.accountname
                pubtoken = allocation.pubtoken

        return render_template('allocation_edit.html', name=allocationname, owner=owner, resources=resources, resource=resource, accountname=accountname, pubtoken=pubtoken)


@app.route('/resource', methods=['GET', 'POST'])
@authenticated
def resource():
    if request.method == 'GET':
        resources = clientapi.listResources()

        return render_template('resource.html', resources=resources)


@app.route('/resource/<name>', methods=['GET', 'POST'])
@authenticated
def resource_name(name):

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


@app.route('/request', methods=['GET', 'POST'])
@authenticated
def vc3request():
    vc3requests = clientapi.listRequests()

    if request.method == 'GET':
        return render_template('request.html', requests=vc3requests)


@app.route('/request/new', methods=['GET', 'POST'])
@authenticated
def request_new():

    if request.method == 'GET':
        allocations = clientapi.listAllocations()
        clusters = clientapi.listClusters()
        return render_template('request_new.html', allocations=allocations, clusters=clusters)

    elif request.method == 'POST':
        allocations = []
        vc3requestname = request.form['name']
        owner = session['name']
        expiration = None
        cluster = request.form['cluster']
        policy = "static-balanced"
        allocations.append(request.form['allocation'])
        environments = ["lincolnb-en1"]

        newrequest = clientapi.defineRequest(name=vc3requestname, owner=owner, cluster=cluster,
                                             allocations=allocations, policy=policy, expiration=expiration, environments=environments)
        clientapi.storeRequest(newrequest)

        flash('Your Virtual Cluster has been successfully been requested!')

        return redirect(url_for('vc3request'))


@app.route('/request/<name>', methods=['GET', 'POST'])
@authenticated
def request_name(name):
    vc3requests = clientapi.listRequests()

    if request.method == 'GET':
        for vc3request in vc3requests:
            if vc3request.name == name:
                requestname = vc3request.name
                owner = vc3request.owner

        return render_template('request_profile.html', name=requestname, owner=owner, requests=vc3requests)


@app.route('/dashboard', methods=['GET', 'POST'])
@authenticated
def dashboard():
    return render_template('dashboard.html')
