import base64
import traceback
import sys
import time

from flask import (flash, redirect, render_template, request,
                   session, url_for)


from portal import app, pages
from portal.decorators import authenticated, allocation_validated
from portal.utils import (load_portal_client, get_safe_redirect,
                          get_vc3_client, project_validated)


# Create a custom error handler for Exceptions
@app.errorhandler(Exception)
def exception_occurred(e):
    trace = traceback.format_tb(sys.exc_info()[2])
    app.logger.error("{0} Traceback occurred:\n".format(time.ctime()) +
                     "{0}\nTraceback completed".format("n".join(trace)))
    trace = "<br>".join(trace)
    trace.replace('\n', '<br>')
    return render_template('error.html', exception=trace,
                           debug=app.config['DEBUG'])


@app.errorhandler(LookupError)
def missing_object_error_page(e):
    return render_template('missing_entity.html')


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
    blog_pages = latest[:10]
    taglist = []
    for p in blog_pages:
        if p.meta['tags'][0] not in taglist:
            taglist.append(p.meta['tags'][0])
    """Send the user to the blog page"""
    return render_template('blog.html', pages=blog_pages, taglist=taglist)


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
    ga_logout_url.append('&redirect_name=VC3 Home')

    # Redirect the user to the Globus Auth logout page
    # return redirect(''.join(ga_logout_url))
    return redirect(url_for('home'))


@app.route('/profile', methods=['GET', 'POST'])
@authenticated
def show_profile_page():
    """User profile information. Assocated with a Globus Auth identity."""

    vc3_client = get_vc3_client()
    userlist = vc3_client.listUsers()

    if request.method == 'GET':
        profile = None

        for user in userlist:
            if session['primary_identity'] == user.identity_id:
                profile = user

        if profile:

            session['name'] = profile.name
            session['displayname'] = profile.displayname
            session['first'] = profile.first
            session['last'] = profile.last
            session['email'] = profile.email
            session['institution'] = profile.organization
            session['primary_identity'] = profile.identity_id
        else:
            if session['primary_identity'] not in ["c887eb90-d274-11e5-bf28-779c8998e810", "05e05adf-e9d4-487f-8771-b6b8a25e84d3", "c4686d14-d274-11e5-b866-0febeb7fd79e", "be58c8e2-fc13-11e5-82f7-f7141a8b0c16", "c456b77c-d274-11e5-b82c-23a245a48997", "f1f26455-cbd5-4933-986b-47c57ee20987", "aebe29b8-d274-11e5-ba4b-ffec0df955f2", "c444a294-d274-11e5-b7f1-e3782ed16687", "9c1c1643-8726-414f-85dc-aca266099304"]:
                next
            else:
                flash('Please complete any missing profile fields before '
                      'launching a cluster.', 'warning')

        if request.args.get('next'):
            session['next'] = get_safe_redirect()

        return render_template('profile.html', userlist=userlist)
    elif request.method == 'POST':
        first = session['first'] = request.form['first']
        last = session['last'] = request.form['last']
        email = session['email'] = request.form['email']
        organization = session['institution'] = request.form['institution']
        identity_id = session['primary_identity']
        name = session['primary_identity']
        displayname = session['displayname'] = request.form['displayname']

        for user in userlist:
            if user.name == name:
                vc3_client.deleteUser(username=name)

        newuser = vc3_client.defineUser(identity_id=identity_id,
                                        name=name,
                                        first=first,
                                        last=last,
                                        email=email,
                                        organization=organization,
                                        displayname=displayname)

        vc3_client.storeUser(newuser)

        flash('Thank you. Your profile has been successfully updated. '
              'You may now register an allocation.', 'success')

        if 'next' in session:
            redirect_to = session['next']
            session.pop('next')
        else:
            redirect_to = url_for('show_profile_page')

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

            session['name'] = profile.name
            session['first'] = profile.first
            session['last'] = profile.last
            session['email'] = profile.email
            session['institution'] = profile.organization
            session['primary_identity'] = profile.identity_id
            session['name'] = profile.name
            session['displayname'] = profile.displayname
        else:
            return redirect(url_for('show_profile_page',
                                    next=url_for('show_profile_page')))

        return redirect(url_for('show_profile_page'))


# -----------------------------------------
# CURRENT PROJECT PAGE AND ALL PROJECT ROUTES
# -----------------------------------------


@app.route('/new', methods=['GET', 'POST'])
@authenticated
@allocation_validated
def create_project():
    """ Creating New Project Form """
    vc3_client = get_vc3_client()
    if request.method == 'GET':
        users = vc3_client.listUsers()
        allocations = vc3_client.listAllocations()
        owner = session['name']

        return render_template('project_new.html', owner=owner,
                               users=users, allocations=allocations)

    elif request.method == 'POST':
        # Method to define and store projects
        # along with associated members and allocations
        # Initial members and allocations not required
        projects = vc3_client.listProjects()
        name = request.form['name']
        owner = session['name']
        members = []

        if request.form['description'] == "":
            description = None
        else:
            description = request.form['description']

        newproject = vc3_client.defineProject(name=name, owner=owner,
                                              members=members, description=description)
        vc3_client.storeProject(newproject)

        for selected_members in request.form.getlist('members'):
            vc3_client.addUserToProject(project=name, user=selected_members)
        for selected_allocations in request.form.getlist('allocation'):
            vc3_client.addAllocationToProject(allocation=selected_allocations,
                                              projectname=newproject.name)
        flash('Your project has been successfully created.', 'success')

        return redirect(url_for('list_projects'))


@app.route('/project', methods=['GET'])
@authenticated
def list_projects():
    """ Project List View """
    vc3_client = get_vc3_client()
    projects = vc3_client.listProjects()
    users = vc3_client.listUsers()
    allocations = vc3_client.listAllocations()

    return render_template('project.html', projects=projects, users=users, allocations=allocations)


@app.route('/project/<name>', methods=['GET'])
@authenticated
def view_project(name):
    """
    View Specific Project Profile View, with name passed in as argument

    :param name: name attribute of project
    :return: Project profile page specific to project name
    """
    project_validation = project_validated(name=name)
    if project_validation == False:
        flash('You do not appear to be a member of the project you are trying'
              'to view. Please contact owner to request membership.', 'warning')
        return redirect(url_for('list_projects'))

    vc3_client = get_vc3_client()
    projects = vc3_client.listProjects()
    allocations = vc3_client.listAllocations()
    users = vc3_client.listUsers()
    project = None

    # Scanning list of projects and matching with name of project argument

    project = vc3_client.getProject(projectname=name)
    if project:
        name = project.name
        owner = project.owner
        members = project.members
        project = project
        description = project.description
        # organization = project.organization
        return render_template('projects_pages.html', name=name, owner=owner,
                               members=members, allocations=allocations,
                               projects=projects, users=users, project=project,
                               description=description)
    app.logger.error("Could not find project when viewing: {0}".format(name))
    raise LookupError('project')


@app.route('/project/<name>/addmember', methods=['POST'])
@authenticated
def add_member_to_project(name):
    """
    Adding members to project from project profile page
    Only owner of project may add members to project

    :param name: name attribute of project
    :return: Project profile page specific to project name
    """

    vc3_client = get_vc3_client()
    projects = vc3_client.listProjects()

    user = request.form['newuser']

    for project in projects:
        if project.name == name:
            name = project.name
            if project.owner == user:
                flash('User is already the project owner.', 'warning')
                app.logger.error("Trying to add owner as member:" +
                                 "owner: {0} project:{1}".format(user, name))
                return redirect(url_for('view_project', name=name))
            for selected_members in request.form.getlist('newuser'):
                vc3_client.addUserToProject(project=name, user=selected_members)
            flash('Successfully added member to project.', 'success')
            return redirect(url_for('view_project', name=name))
    app.logger.error("Could not find project when adding user: " +
                     "user: {0} project:{1}".format(user, name))
    flash('Project not found, can\'t add user', 'warning')
    return redirect(url_for('view_project', name=name))


@app.route('/project/<name>/removemember', methods=['POST'])
@authenticated
def remove_member_from_project(name):
    """
    Removing members from project
    Only owner of project may remove members to project

    :param name: name attribute of project
    :return: Project profile page specific to project name
    """

    vc3_client = get_vc3_client()
    project = vc3_client.getProject(projectname=name)
    user = request.form['newuser']

    vc3_client.removeUserFromProject(user=user, project=project.name)

    return redirect(url_for('view_project', name=name))


@app.route('/project/<name>/addallocation', methods=['POST'])
@authenticated
def add_allocation_to_project(name):
    """
    Adding allocations to project from project profile page
    Only owner/members of project may add their own allocations to project

    :param name: name attribute of project to match
    :return: Project page specific to project name, with new allocation added
    """
    vc3_client = get_vc3_client()
    projects = vc3_client.listProjects()

    # new_allocation = request.form['allocation']

    for project in projects:
        if project.name == name:
            name = project.name
            for selected_allocations in request.form.getlist('allocation'):
                vc3_client.addAllocationToProject(allocation=selected_allocations,
                                                  projectname=name)
            flash('Successfully added allocation to project.', 'success')
            return redirect(url_for('view_project', name=name))
    app.logger.error("Could not find project when adding allocation: " +
                     "alloc: {0} project:{1}".format(new_allocation, name))
    flash('Project not found, could not add allocation to project', 'warning')
    return redirect(url_for('view_project', name=name))


@app.route('/project/<name>/removeallocation', methods=['POST'])
@authenticated
def remove_allocation_from_project(name):
    """
    Removing allocation from project
    Only owner of project and/or owner of allocation may remove allocations
    from said project

    :param name: name attribute of project
    :return: Project profile page specific to project name
    """

    vc3_client = get_vc3_client()
    remove_allocation = request.form['remove_allocation']

    vc3_client.removeAllocationFromProject(allocation=remove_allocation, projectname=name)
    flash('You have successfully removed allocation from this project', 'success')

    return redirect(url_for('view_project', name=name))


@app.route('/project/delete/<name>', methods=['GET'])
@authenticated
def delete_project(name):
    """
    Route for method to delete project

    :param name: name attribute of project to delete
    :return: Redirect to List Project page with project deleted
    """

    project_validation = project_validated(name=name)
    if project_validation == False:
        flash('You do not have the authority to delete this project.', 'warning')
        return redirect(url_for('list_projects'))

    vc3_client = get_vc3_client()

    # Grab project by name and delete entity

    project = vc3_client.getProject(projectname=name)
    vc3_client.deleteProject(projectname=project.name)
    flash('Project has been successfully deleted', 'success')

    return redirect(url_for('list_projects'))


@app.route('/cluster/new', methods=['GET', 'POST'])
@authenticated
@allocation_validated
def create_cluster():
    """ Create New Cluster Template Form """

    vc3_client = get_vc3_client()
    clusters = vc3_client.listClusters()
    projects = vc3_client.listProjects()
    nodesets = vc3_client.listNodesets()

    if request.method == 'GET':
        return render_template('cluster_new.html', clusters=clusters,
                               projects=projects, nodesets=nodesets)

    elif request.method == 'POST':
        # Assigning attribute variables by form input and presets
        # Create and save new nodeset first, followed by new cluster
        # and finally add said nodeset to the new cluster

        inputname = request.form['name']
        owner = session['name']
        node_number = request.form['node_number']
        app_type = request.form['app_type']
        app_role = "worker-nodes"
        environment = "condor-glidein-password-env1"
        translatename = "".join(inputname.split())
        name = translatename.lower()
        description_input = request.form['description']
        description = str(description_input)

        nodeset = vc3_client.defineNodeset(name=name, owner=owner,
                                           node_number=node_number, app_type=app_type,
                                           app_role=app_role, environment=environment)
        vc3_client.storeNodeset(nodeset)
        newcluster = vc3_client.defineCluster(
            name=name, owner=owner, nodesets=[], description=description)
        vc3_client.storeCluster(newcluster)
        vc3_client.addNodesetToCluster(nodesetname=nodeset.name,
                                       clustername=newcluster.name)

        flash('Your cluster template has been successfully defined.', 'success')
        return redirect(url_for('list_clusters'))


@app.route('/cluster', methods=['GET'])
@authenticated
def list_clusters():
    """ List Cluster Template View """
    vc3_client = get_vc3_client()
    clusters = vc3_client.listClusters()
    projects = vc3_client.listProjects()
    nodesets = vc3_client.listNodesets()

    return render_template('cluster.html', clusters=clusters,
                           projects=projects, nodesets=nodesets)


@app.route('/cluster/<name>', methods=['GET', 'POST'])
@authenticated
@allocation_validated
def view_cluster(name):
    """
    Specific page view, pertaining to Cluster Template

    :param name: name attribute of cluster
    :return: Cluster Template profile view specific to cluster name
    """
    vc3_client = get_vc3_client()
    clusters = vc3_client.listClusters()
    projects = vc3_client.listProjects()
    nodesets = vc3_client.listNodesets()
    users = vc3_client.listUsers()
    cluster = None

    if request.method == 'GET':
        cluster = vc3_client.getCluster(clustername=name)
        if cluster:
            cluster_name = cluster.name
            owner = cluster.owner
            state = cluster.state
            description = cluster.description

            return render_template('cluster_profile.html', name=cluster_name,
                                   owner=owner, state=state,
                                   nodesets=nodesets, description=description,
                                   users=users, clusters=clusters,
                                   projects=projects)
        raise LookupError('cluster')

    elif request.method == 'POST':
        node_number = request.form['node_number']
        app_type = request.form['app_type']
        description = request.form['description']

        if app_type == "htcondor":
            environment = "condor-glidein-password-env1"
        elif app_type == "workqueue":
            environment = []
        else:
            app.logger.error("Got unsupported framework when viewing " +
                             "cluster template: {0}".format(app_type))
            raise ValueError('app_type not a recognized framework')

        cluster_name = None
        owner = None
        app_role = None

        for cluster in clusters:
            if cluster.name == name:
                cluster_name = cluster.name
                owner = cluster.owner
                app_role = "worker-nodes"
                break
        if cluster_name is None:
            # could not find cluster, punt
            LookupError('cluster')

        vc3_client.deleteNodeset(nodesetname=name)
        vc3_client.deleteCluster(clustername=name)
        nodeset = vc3_client.defineNodeset(name=cluster_name, owner=owner,
                                           node_number=node_number,
                                           app_type=app_type, app_role=app_role,
                                           environment=environment)
        vc3_client.storeNodeset(nodeset)
        newcluster = vc3_client.defineCluster(
            name=cluster_name, owner=owner, description=description)
        vc3_client.storeCluster(newcluster)
        vc3_client.addNodesetToCluster(nodesetname=nodeset.name,
                                       clustername=newcluster.name)

        # return render_template('cluster_profile.html', name=cluster_name,
        #                        owner=owner, clusters=clusters,
        #                        projects=projects)
        # flash('Your cluster template has been successfully updated.', 'success')
        return redirect(url_for('view_cluster', name=name))


@app.route('/cluster/edit/<name>', methods=['GET'])
@authenticated
def edit_cluster(name):
    """
    Edit Page for specific cluster templates
    Only owner of cluster template may make edits to cluster template

    :param name: name attribute of cluster template to match
    :return: Edit Page with information pertaining to the cluster template
    """
    vc3_client = get_vc3_client()
    clusters = vc3_client.listClusters()
    projects = vc3_client.listProjects()
    nodesets = vc3_client.listNodesets()
    frameworks = []

    for cluster in clusters:
        if cluster.name == name:
            clustername = cluster.name
            owner = cluster.owner
            state = cluster.state
            acl = cluster.acl
            description = cluster.description
    for nodeset in nodesets:
        if nodeset.name == name:
            node_number = nodeset.node_number
            framework = nodeset.app_type
            if nodeset.app_type not in frameworks:
                frameworks.append(nodeset.app_type)

            return render_template('cluster_edit.html', name=clustername,
                                   owner=owner, nodesets=nodesets,
                                   state=state, acl=acl, projects=projects,
                                   frameworks=frameworks, node_number=node_number,
                                   description=description, framework=framework)
    app.logger.error("Could not find cluster when editing: {0}".format(name))
    raise LookupError('cluster')


@app.route('/cluster/delete/<name>', methods=['GET'])
@authenticated
def delete_cluster(name):
    """
    Route for method to delete cluster template

    :param name: name attribute of cluster template to delete
    :return: Redirect to List Cluster Template page with cluster template deleted
    """
    vc3_client = get_vc3_client()

    # Grab nodeset associated with cluster template and delete entity

    nodeset = vc3_client.getNodeset(nodesetname=name)
    vc3_client.deleteNodeset(nodesetname=nodeset.name)

    # Finally grab cluster template and delete entity

    cluster = vc3_client.getCluster(clustername=name)
    vc3_client.deleteCluster(clustername=cluster.name)
    flash('Cluster Template has been successfully deleted', 'success')

    return redirect(url_for('list_clusters'))


@app.route('/allocation', methods=['GET'])
@authenticated
def list_allocations():
    """ List Allocations Page """
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
    """ New Alloation Creation Form """
    vc3_client = get_vc3_client()
    if request.method == 'GET':
        resources = vc3_client.listResources()
        return render_template('allocation_new.html', resources=resources)

    elif request.method == 'POST':
        # Gathering and storing information from new allocation form
        # into info-service
        # Description from text input stored as string to avoid malicious input

        displayname = request.form['displayname']
        owner = session['name']
        resource = request.form['resource']
        accountname = request.form['accountname']
        allocationname = owner + "." + resource
        name = allocationname.lower()
        description_input = request.form['description']
        description = str(description_input)
        # url = request.form['url']

        newallocation = vc3_client.defineAllocation(
            name=name, owner=owner, resource=resource, accountname=accountname,
            displayname=displayname, description=description)
        vc3_client.storeAllocation(newallocation)

        flash('Configuring your allocation, when complete, please view your '
              'allocation to complete the setup.', 'warning')

        return redirect(url_for('list_allocations'))


@app.route('/allocation/<name>', methods=['GET', 'POST'])
@authenticated
# @allocation_validated
def view_allocation(name):
    """
    Allocation Detailed Page View

    :param name: name attribute of allocation
    :return: Allocation detailed page with associated attributes
    """
    vc3_client = get_vc3_client()
    allocations = vc3_client.listAllocations()
    resources = vc3_client.listResources()
    users = vc3_client.listUsers()

    if request.method == 'GET':
        for allocation in allocations:
            if allocation.name == name:
                allocationname = allocation.name
                owner = allocation.owner
                resource = allocation.resource
                state = allocation.state
                displayname = allocation.displayname
                description = allocation.description
                accountname = allocation.accountname
                encodedpubtoken = allocation.pubtoken
                if encodedpubtoken is None:
                    pubtoken = 'None'
                else:
                    pubtoken = base64.b64decode(encodedpubtoken)

                return render_template('allocation_profile.html',
                                       name=allocationname,
                                       owner=owner, resource=resource,
                                       accountname=accountname,
                                       pubtoken=pubtoken, state=state,
                                       resources=resources, displayname=displayname,
                                       description=description, users=users)
        app.logger.error("Could not find allocation when viewing: {0}".format(name))
        raise LookupError('allocation')

    elif request.method == 'POST':
        # Iterate through allocations list in infoservice for allocation
        # with the matching name argument and update with new form input

        for allocation in allocations:
            if allocation.name == name:
                allocationname = allocation.name
                owner = allocation.owner
                resource = request.form['resource']
                accountname = request.form['accountname']
                # displayname = request.form['displayname']
                # description_input = request.form['description']
                # description = str(description_input)

                newallocation = vc3_client.defineAllocation(name=allocationname,
                                                            owner=owner,
                                                            resource=resource,
                                                            accountname=accountname)
                vc3_client.storeAllocation(newallocation)
                flash('Allocation created', 'success')
                return render_template('allocation_profile.html', name=allocationname,
                                       owner=owner, accountname=accountname,
                                       resource=resource, allocations=allocations,
                                       resources=resources)


@app.route('/allocation/edit/<name>', methods=['GET'])
@authenticated
@allocation_validated
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
                                   owner=owner, resources=resources,
                                   resource=resource, accountname=accountname,
                                   pubtoken=pubtoken)
    app.logger.error("Could not find allocation when editing: {0}".format(name))
    raise LookupError('alliocation')


@app.route('/resource', methods=['GET'])
@authenticated
def list_resources():
    """ Route for HPC and Resources List View """
    vc3_client = get_vc3_client()
    resources = vc3_client.listResources()

    return render_template('resource.html', resources=resources)


@app.route('/resource/<name>', methods=['GET'])
@authenticated
def view_resource(name):
    """
    Route to view specific Resource profiles

    :param name: name attribute of Resource to view
    :return: Directs to detailed profile view of said Resource
    """
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
                                   resource=resource, description=description,
                                   displayname=displayname, url=url,
                                   docurl=docurl, organization=organization)
    app.logger.error("Could not find Resource when viewing: {0}".format(name))
    raise LookupError('resource')


@app.route('/request', methods=['GET'])
@authenticated
def list_requests():
    """ List View of Virtual Clusters """
    vc3_client = get_vc3_client()
    vc3_requests = vc3_client.listRequests()
    nodesets = vc3_client.listNodesets()
    clusters = vc3_client.listClusters

    return render_template('request.html', requests=vc3_requests,
                           nodesets=nodesets, clusters=clusters)


@app.route('/request/new', methods=['GET', 'POST'])
@authenticated
def create_request():
    """
    Form to launch new Virtual Cluster

    Users must have both, a validated allocation and cluster template to launch
    """
    vc3_client = get_vc3_client()
    if request.method == 'GET':
        allocations = vc3_client.listAllocations()
        clusters = vc3_client.listClusters()
        return render_template('request_new.html', allocations=allocations,
                               clusters=clusters)

    elif request.method == 'POST':
        # Define and store new Virtual Clusters within infoservice
        # Policies currently default to "static-balanced"
        # Environments currently default to "condor-glidein-password-env1"
        # Return redirects to Virtual Clusters List View after creation
        allocations = []
        inputname = request.form['name']
        owner = session['name']
        expiration = None
        cluster = request.form['cluster']
        policy = "static-balanced"
        translatename = "".join(inputname.split())
        vc3requestname = translatename.lower()
        environments = ["condor-glidein-password-env1"]
        for selected_allocations in request.form.getlist('allocation'):
            allocations.append(selected_allocations)

        newrequest = vc3_client.defineRequest(name=vc3requestname,
                                              owner=owner, cluster=cluster,
                                              allocations=allocations,
                                              environments=environments,
                                              policy=policy,
                                              expiration=expiration)
        vc3_client.storeRequest(newrequest)

        flash('Your Virtual Cluster has been successfully launched.', 'success')

        return redirect(url_for('list_requests'))


@app.route('/request/<name>', methods=['GET', 'POST'])
@authenticated
def view_request(name):
    """
    Route for specific detailed page view of Virtual Clusters

    :param name: name attribute of Virtual Cluster
    :return: Directs to detailed page view of Virtual Clusters with
    associated attributes
    """
    vc3_client = get_vc3_client()
    vc3_requests = vc3_client.listRequests()
    nodesets = vc3_client.listNodesets()
    clusters = vc3_client.listClusters
    users = vc3_client.listUsers()

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
                                       action=action, state=state, users=users)
        app.logger.error("Could not find VC when viewing: {0}".format(name))
        raise LookupError('virtual cluster')

    elif request.method == 'POST':
        # Method to terminate running a specific Virtual Cluster
        # based on name argument that is passed through
        for vc3_request in vc3_requests:
            if vc3_request.name == name:
                requestname = vc3_request.name

                vc3_client.terminateRequest(requestname=requestname)

                flash('Your Virtual Cluster has successfully begun termination.',
                      'success')
                return redirect(url_for('list_requests'))
        flash('Could not find specified Virtual Cluster', 'warning')
        app.logger.error("Could not find VC when terminating: {0}".format(name))
        return redirect(url_for('list_requests'))


@app.route('/monitoring', methods=['GET'])
@authenticated
def dashboard():
    return render_template('dashboard.html')


@app.route('/timeline', methods=['GET'])
@authenticated
def timeline():
    return render_template('timeline.html')


@app.route('/error', methods=['GET'])
@authenticated
def errorpage():

    if request.method == 'GET':
        return render_template('error.html')
