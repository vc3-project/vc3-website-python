import base64
import traceback
import sys
import time
from ConfigParser import SafeConfigParser
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from flask import (abort, flash, redirect, render_template, request,
                   session, url_for)

from vc3client import client

from portal import app, pages
from portal.decorators import authenticated
from portal.utils import (load_portal_client, get_safe_redirect)


# Create a custom error handler for Exceptions
@app.errorhandler(Exception)
def exception_occurred(e):
    trace = traceback.format_tb(sys.exc_info()[2])
    app.logger.error("{0} Traceback occurred:\n".format(time.ctime()) +
                     "{0}\nTraceback completed".format("n".join(trace)))
    trace = "<br>".join(trace)
    trace.replace('\n', '<br>')
    return render_template('error.html', exception=trace, debug=True)


@app.errorhandler(LookupError)
def missing_object_error_page(e):
    return render_template('missing_entity.html')


def get_vc3_client():
    """
    Return a VC3 client instance

    :return: VC3 client instance on success
    """
    c = SafeConfigParser()
    # TODO: change this to use a environ or config param
    c.readfp(open('/etc/vc3/vc3-client.conf'))

    try:
        client_api = client.VC3ClientAPI(c)
        return client_api
    except Exception as e:
        abort(500)


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
    page_path = pages.get_or_404(path)
    return render_template('blog_page.html', page=page_path)


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
def show_profile_page():
    """User profile information. Assocated with a Globus Auth identity."""

    vc3_client = get_vc3_client()
    if request.method == 'GET':
        userlist = vc3_client.listUsers()
        profile = None

        for user in userlist:
            if session['primary_identity'] == user.identity_id:
                profile = user

        if profile:

            # session['name'] = profile.name
            username = profile.name[0] + profile.last
            session['name'] = username.lower()
            session['first'] = profile.first
            session['last'] = profile.last
            session['email'] = profile.email
            session['institution'] = profile.organization
            session['primary_identity'] = profile.identity_id
        else:
            flash('Please complete any missing profile fields before '
                  'launching a cluster.', 'warning')

        if request.args.get('next'):
            session['next'] = get_safe_redirect()

        return render_template('profile.html')
    elif request.method == 'POST':
        first = session['first'] = request.form['first']
        last = session['last'] = request.form['last']
        email = session['email'] = request.form['email']
        organization = session['institution'] = request.form['institution']
        identity_id = session['primary_identity']
        username = first[0] + last
        name = username.lower()

        newuser = vc3_client.defineUser(identity_id=identity_id,
                                        name=name,
                                        first=first,
                                        last=last,
                                        email=email,
                                        organization=organization)

        vc3_client.storeUser(newuser)

        flash('Thank you. Your profile has been successfully updated. '
              'You may now register an allocation.', 'success')

        if 'next' in session:
            redirect_to = session['next']
            session.pop('next')
        else:
            redirect_to = url_for('profile')

        return redirect(redirect_to)


@app.route('/profile/edit', methods=['GET'])
@authenticated
def edit_profile():
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
        vc3_client = get_vc3_client()
        userlist = vc3_client.listUsers()
        profile = None

        for user in userlist:
            if session['primary_identity'] == user.identity_id:
                profile = user

        if profile:

            # session['name'] = profile.name
            session['first'] = profile.first
            session['last'] = profile.last
            session['email'] = profile.email
            session['institution'] = profile.organization
            session['primary_identity'] = profile.identity_id
            username = profile.name[0] + profile.last
            session['name'] = username.lower()
        else:
            return redirect(url_for('profile',
                                    next=url_for('profile')))

        return redirect(url_for('profile'))


# -----------------------------------------
# CURRENT PROJECT PAGE AND ALL PROJECT ROUTES
# -----------------------------------------


@app.route('/new', methods=['GET', 'POST'])
@authenticated
def create_project():
    vc3_client = get_vc3_client()
    if request.method == 'GET':
        users = vc3_client.listUsers()
        return render_template('new.html', users=users)

    elif request.method == 'POST':
        name = request.form['name']
        owner = session['name']
        members = request.form['members'].split(",")
        # description = request.form['description']
        # organization = request.form['organization']

        newproject = vc3_client.defineProject(name=name, owner=owner,
                                              members=members)
        vc3_client.storeProject(newproject)

        flash('Your project has been successfully created!', 'success')

        return redirect(url_for('project'))


@app.route('/project', methods=['GET'])
@authenticated
def list_projects():
    vc3_client = get_vc3_client()
    projects = vc3_client.listProjects()

    return render_template('project.html', projects=projects)


@app.route('/project/<name>', methods=['GET'])
@authenticated
def view_project(name):
    vc3_client = get_vc3_client()
    projects = vc3_client.listProjects()
    allocations = vc3_client.listAllocations()
    users = vc3_client.listUsers()

    for project in projects:
        if project.name == name:
            name = project.name
            owner = project.owner
            members = project.members
            # description = project.description
            # organization = project.organization
    return render_template('projects_pages.html', name=name, owner=owner,
                           members=members, allocations=allocations,
                           projects=projects, users=users)


@app.route('/project/<name>/addmember', methods=['POST'])
@authenticated
def add_member_to_project(name):
    vc3_client = get_vc3_client()
    projects = vc3_client.listProjects()

    user = request.form['newuser']

    for project in projects:
        if project.name == name:
            name = project.name
            vc3_client.addUserToProject(project=name, user=user)

    flash('Successfully added member to project.', 'success')

    return redirect(url_for('project_name', name=name))


@app.route('/project/<name>/addallocation', methods=['POST'])
@authenticated
def add_allocation_to_project(name):
    vc3_client = get_vc3_client()
    projects = vc3_client.listProjects()

    addallocation = request.form['allocation']

    for project in projects:
        if project.name == name:
            name = project.name
            vc3_client.addAllocationToProject(allocation=addallocation,
                                              projectname=name)

    flash('Successfully added allocation to project.', 'success')

    return redirect(url_for('view_project', name=name))


@app.route('/cluster/new', methods=['GET', 'POST'])
@authenticated
def create_cluster():
    vc3_client = get_vc3_client()
    clusters = vc3_client.listClusters()
    projects = vc3_client.listProjects()
    nodesets = vc3_client.listNodesets()

    if request.method == 'GET':
        return render_template('cluster_new.html', clusters=clusters,
                               projects=projects, nodesets=nodesets)

    elif request.method == 'POST':
        inputname = request.form['name']
        owner = session['name']
        node_number = request.form['node_number']
        app_type = request.form['app_type']
        app_role = "worker-nodes"
        environment = "condor-glidein-password-env1"
        translatename = "".join(inputname.split())
        name = translatename.lower()

        nodeset = vc3_client.defineNodeset(name=name, owner=owner,
                                           node_number=node_number, app_type=app_type,
                                           app_role=app_role, environment=environment)
        vc3_client.storeNodeset(nodeset)
        # nodesets = vc3_client.listNodesets()
        newcluster = vc3_client.defineCluster(name=name, owner=owner, nodesets=[])
        vc3_client.storeCluster(newcluster)
        vc3_client.addNodesetToCluster(nodesetname=nodeset.name,
                                       clustername=newcluster.name)

        flash('Your cluster template has been successfully defined!', 'success')
        return redirect(url_for('cluster'))


@app.route('/cluster', methods=['GET'])
@authenticated
def list_clusters():
    vc3_client = get_vc3_client()
    clusters = vc3_client.listClusters()
    projects = vc3_client.listProjects()
    nodesets = vc3_client.listNodesets()

    return render_template('cluster.html', clusters=clusters,
                           projects=projects, nodesets=nodesets)


@app.route('/cluster/<name>', methods=['GET', 'POST'])
@authenticated
def view_cluster(name):
    vc3_client = get_vc3_client()
    clusters = vc3_client.listClusters()
    projects = vc3_client.listProjects()
    nodesets = vc3_client.listNodesets()

    if request.method == 'GET':
        for cluster in clusters:
            if cluster.name == name:
                clustername = cluster.name
                owner = cluster.owner
                state = cluster.state

        return render_template('cluster_profile.html', name=clustername,
                               owner=owner, state=state, nodesets=nodesets)

    elif request.method == 'POST':
        node_number = request.form['node_number']
        app_type = request.form['app_type']

        if app_type == "htcondor":
            environment = "condor-glidein-password-env1"
        elif app_type == "workqueue":
            environment = []

        for cluster in clusters:
            if cluster.name == name:
                clustername = cluster.name
                owner = cluster.owner
                app_role = "worker-nodes"

        nodeset = vc3_client.defineNodeset(name=clustername, owner=owner,
                                           node_number=node_number,
                                           app_type=app_type, app_role=app_role,
                                           environment=environment)
        vc3_client.storeNodeset(nodeset)
        newcluster = vc3_client.defineCluster(name=clustername, owner=owner)
        vc3_client.storeCluster(newcluster)
        vc3_client.addNodesetToCluster(nodesetname=nodeset.name,
                                       clustername=newcluster.name)

        return render_template('cluster_profile.html', name=clustername,
                               owner=owner, clusters=clusters,
                               projects=projects)


@app.route('/cluster/edit/<name>', methods=['GET'])
@authenticated
def edit_cluster(name):
    vc3_client = get_vc3_client()
    clusters = vc3_client.listClusters()
    projects = vc3_client.listProjects()
    nodesets = vc3_client.listNodesets()

    for cluster in clusters:
        if cluster.name == name:
            clustername = cluster.name
            owner = cluster.owner
            state = cluster.state
            acl = cluster.acl

    return render_template('cluster_edit.html', name=clustername,
                           owner=owner, nodesets=nodesets,
                           state=state, acl=acl, projects=projects)


@app.route('/allocation', methods=['GET'])
@authenticated
def list_allocations():
    vc3_client = get_vc3_client()
    allocations = vc3_client.listAllocations()
    resources = vc3_client.listResources()
    projects = vc3_client.listProjects()
    users = vc3_client.listUsers()

    return render_template('allocation.html', allocations=allocations,
                           resources=resources, users=users, projects=projects)


@app.route('/allocation/new', methods=['GET', 'POST'])
@authenticated
def create_allocation():
    vc3_client = get_vc3_client()
    if request.method == 'GET':
        resources = vc3_client.listResources()
        for resource in resources:
            resourcename = resource.name
        return render_template('allocation_new.html', resources=resources,
                               name=resourcename)

    elif request.method == 'POST':
        # name = request.form['name']
        owner = session['name']
        resource = request.form['resource']
        accountname = request.form['accountname']
        allocationname = owner + "." + resource
        name = allocationname.lower()
        # description = request.form['description']
        # url = request.form['url']

        newallocation = vc3_client.defineAllocation(
            name=name, owner=owner, resource=resource, accountname=accountname)
        vc3_client.storeAllocation(newallocation)

        flash('You may find your SSH key in your new allocation profile '
              'after validation.', 'info')

        return redirect(url_for('allocation'))


@app.route('/allocation/<name>', methods=['GET', 'POST'])
@authenticated
def view_allocation(name):
    vc3_client = get_vc3_client()
    allocations = vc3_client.listAllocations()
    resources = vc3_client.listResources()

    if request.method == 'GET':
        for allocation in allocations:
            if allocation.name == name:
                allocationname = allocation.name
                owner = allocation.owner
                resource = allocation.resource
                state = allocation.state
                accountname = allocation.accountname
                encodedpubtoken = allocation.pubtoken
                if encodedpubtoken is None:
                    pubtoken = None
                else:
                    pubtoken = base64.b64decode(encodedpubtoken)

        return render_template('allocation_profile.html', name=allocationname,
                               owner=owner, resource=resource,
                               accountname=accountname, pubtoken=pubtoken,
                               state=state)

    elif request.method == 'POST':

        for allocation in allocations:
            if allocation.name == name:
                allocationname = allocation.name
                owner = allocation.owner
                resource = request.form['resource']
                accountname = request.form['accountname']

        newallocation = vc3_client.defineAllocation(name=allocationname,
                                                    owner=owner,
                                                    resource=resource,
                                                    accountname=accountname)
        vc3_client.storeAllocation(newallocation)

        return render_template('allocation_profile.html', name=allocationname,
                               owner=owner, accountname=accountname,
                               resource=resource, allocations=allocations,
                               resources=resources)


@app.route('/allocation/edit/<name>', methods=['GET'])
@authenticated
def edit_allocation(name):
    vc3_client = get_vc3_client()
    allocations = vc3_client.listAllocations()
    resources = vc3_client.listResources()

    for allocation in allocations:
        if allocation.name == name:
            allocationname = allocation.name
            owner = allocation.owner
            resource = allocation.resource
            accountname = allocation.accountname
            pubtoken = allocation.pubtoken

    return render_template('allocation_edit.html', name=allocationname,
                           owner=owner, resources=resources, resource=resource,
                           accountname=accountname, pubtoken=pubtoken)


@app.route('/resource', methods=['GET'])
@authenticated
def list_resources():
    vc3_client = get_vc3_client()
    resources = vc3_client.listResources()

    return render_template('resource.html', resources=resources)


@app.route('/resource/<name>', methods=['GET'])
@authenticated
def view_resource(name):
    vc3_client = get_vc3_client()
    resources = vc3_client.listResources()

    for resource in resources:
        if resource.name == name:
            resourcename = resource.name
            owner = resource.owner
            accessflavor = resource.accessflavor
            description = resource.description
            displayname = resource.displayname
            url = resource.url
            docurl = resource.docurl
            organization = resource.organization

    return render_template('resource_profile.html', name=resourcename,
                           owner=owner, accessflavor=accessflavor,
                           resource=resource,
                           description=description, displayname=displayname,
                           url=url, docurl=docurl, organization=organization)


@app.route('/request', methods=['GET'])
@authenticated
def list_requests():
    vc3_client = get_vc3_client()
    vc3_requests = vc3_client.listRequests()
    nodesets = vc3_client.listNodesets()
    clusters = vc3_client.listClusters

    return render_template('request.html', requests=vc3_requests,
                           nodesets=nodesets, clusters=clusters)


@app.route('/request/new', methods=['GET', 'POST'])
@authenticated
def create_request():
    vc3_client = get_vc3_client()
    if request.method == 'GET':
        allocations = vc3_client.listAllocations()
        clusters = vc3_client.listClusters()
        return render_template('request_new.html', allocations=allocations,
                               clusters=clusters)

    elif request.method == 'POST':
        allocations = []
        # environments = []
        vc3requestname = request.form['name']
        owner = session['name']
        expiration = None
        cluster = request.form['cluster']
        policy = "static-balanced"
        environments = ["condor-glidein-password-env1"]
        for selectedallocations in request.form.getlist('allocation'):
            allocations.append(selectedallocations)

        newrequest = vc3_client.defineRequest(name=vc3requestname,
                                              owner=owner, cluster=cluster,
                                              allocations=allocations,
                                              environments=environments, policy=policy,
                                              expiration=expiration)
        vc3_client.storeRequest(newrequest)

        flash('Your Virtual Cluster has been successfully requested!', 'success')

        return redirect(url_for('vc3request'))


@app.route('/request/<name>', methods=['GET', 'POST'])
@authenticated
def view_request(name):
    vc3_client = get_vc3_client()
    vc3_requests = vc3_client.listRequests()
    nodesets = vc3_client.listNodesets()
    clusters = vc3_client.listClusters

    if request.method == 'GET':
        for vc3_request in vc3_requests:
            if vc3_request.name == name:
                requestname = vc3_request.name
                owner = vc3_request.owner
                action = vc3_request.action
                state = vc3_request.state

        return render_template('request_profile.html', name=requestname,
                               owner=owner, requests=vc3_requests,
                               clusters=clusters, nodesets=nodesets,
                               action=action, state=state)

    elif request.method == 'POST':
        for vc3_request in vc3_requests:
            if vc3_request.name == name:
                requestname = vc3_request.name

        vc3_client.terminateRequest(requestname=requestname)

        flash('Your Virtual Cluster has successfully begun termination.',
              'success')

        return redirect(url_for('vc3request'))


@app.route('/dashboard', methods=['GET'])
@authenticated
def dashboard():
    return render_template('dashboard.html')


@app.route('/error', methods=['GET'])
@authenticated
def errorpage():

    if request.method == 'GET':
        return render_template('error.html')
