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
# c.readfp(open('/Users/JeremyVan/Documents/Programming/UChicago/VC3_Project/vc3-website-python/vc3-client/etc/vc3-client.conf'))
clientapi = client.VC3ClientAPI(c)


@app.route('/', methods=['GET'])
def home():
    """Home page - play with it if you must!"""
    return render_template('home.jinja2')

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
    return render_template('blog.jinja2', pages=latest[:10])


@app.route('/blog/tag/<string:tag>/', methods=['GET'])
def tag(tag):
    """Automatic routing and compiling for article tags"""
    tagged = [p for p in pages if tag in p.meta.get('tags', [])]
    return render_template('blog_tag.jinja2', pages=tagged, tag=tag)


@app.route('/blog/<path:path>/', methods=['GET'])
def page(path):
    """Automatic routing and generates markdown flatpages in /pages directory"""
    page = pages.get_or_404(path)
    return render_template('blog_page.jinja2', page=page)


@app.route('/community', methods=['GET'])
def community():
    """Send the user to community page"""
    return render_template('community.jinja2')


@app.route('/documentations', methods=['GET'])
def documentations():
    """Send the user to documentations page"""
    return render_template('documentations.jinja2')


@app.route('/team', methods=['GET'])
def team():
    """Send the user to team page"""
    return render_template('team.jinja2')


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

        return render_template('profile.jinja2')
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
    return render_template('new.jinja2')


@app.route('/project', methods=['GET', 'POST'])
@authenticated
def project():

    if request.method == 'POST':
        name = request.form['name']
        owner = request.form['owner']
        members = request.form['members'].split(",")

        newproject = clientapi.defineProject(name=name, owner=owner, members=members)
        clientapi.storeProject(newproject)

        return render_template('project.jinja2')
    elif request.method == 'GET':
        projects = clientapi.listProjects()
        # for project in projects:
        #     print(project)
        return render_template('project.jinja2', projects=projects)


@app.route('/project/<name>', methods=['GET', 'POST'])
@authenticated
def project_name(name):
    projects = clientapi.listProjects()
    # userproject = clientapi.getProjectsOfUser(projects)

    if request.method == 'GET':
        for project in projects:
            if project.name == name:
                projectname = project.name
                owner = project.owner
                members = project.members

    # elif request.method == 'POST':
    #     for project in projects:
    #         newmember = request.form['members']
    #         project = project
    #
    #     clientapi.addUserToProject(project=project, user=newmember)

    return render_template('projects_pages.jinja2', name=projectname, owner=owner, members=members, project=project)


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

        return render_template('allocation.jinja2')
    elif request.method == 'GET':
        allocations = clientapi.listAllocations()
        for allocation in allocations:
            print(allocation)
        return render_template('allocation.jinja2', allocations=allocations)
    return render_template('allocation.jinja2')


@app.route('/allocation/new', methods=['GET', 'POST'])
@authenticated
def new_allocation():
    return render_template('new_allocation.jinja2')


@app.route('/dashboard', methods=['GET', 'POST'])
@authenticated
def dashboard():
    return render_template('dashboard.jinja2')
