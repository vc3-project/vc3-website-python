from flask import (abort, flash, redirect, render_template, request,
                   session, url_for, g)
import requests

import os

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

import vc3client


@app.route('/', methods=['GET'])
def home():
    """Home page - play with it if you must!"""
    return render_template('home.jinja2')

# -----------------------------------------
# CURRENT NEWS PAGE AND ALL ARTICLE ROUTES
# -----------------------------------------


@app.route('/news', methods=['GET'])
def news():
    """Articles are pages with a publication date"""
    articles = (p for p in pages if 'date' in p.meta)
    """Show the 10 most recent articles, most recent first"""
    latest = sorted(articles, reverse=True, key=lambda p: p.meta['date'])
    """Send the user to the news page"""
    return render_template('news.jinja2', pages=latest[:10])


@app.route('/news/tag/<string:tag>/', methods=['GET'])
def tag(tag):
    """Automatic routing and compiling for article tags"""
    tagged = [p for p in pages if tag in p.meta.get('tags', [])]
    return render_template('news_tag.jinja2', pages=tagged, tag=tag)


@app.route('/news/<path:path>/', methods=['GET'])
def page(path):
    """Automatic routing and generates markdown flatpages in /pages directory"""
    page = pages.get_or_404(path)
    return render_template('news_page.jinja2', page=page)


@app.route('/documentations', methods=['GET'])
def documentations():
    """Send the user to documentations page"""
    return render_template('documentations.jinja2')


@app.route('/team', methods=['GET'])
def team():
    """Send the user to team page"""
    return render_template('team.jinja2')


@app.route('/contact', methods=['GET'])
def contact():
    """Send the user to contact page"""
    return render_template('contact.jinja2')


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
    client = load_portal_client()

    # Revoke the tokens with Globus Auth
    for token, token_type in (
            (token_info[ty], ty)
            # get all of the token info dicts
            for token_info in session['tokens'].values()
            # cross product with the set of token types
            for ty in ('access_token', 'refresh_token')
            # only where the relevant token is actually present
            if token_info[ty] is not None):
        client.oauth2_revoke_token(
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
        identity_id = session.get('primary_identity')
        profile = database.load_profile(identity_id)

        if profile:
            name, email, institution = profile

            session['name'] = name
            session['email'] = email
            session['institution'] = institution
        else:
            flash(
                'Please complete any missing profile fields and press Save.')

        if request.args.get('next'):
            session['next'] = get_safe_redirect()

        return render_template('profile.jinja2')
    elif request.method == 'POST':
        name = session['name'] = request.form['name']
        email = session['email'] = request.form['email']
        institution = session['institution'] = request.form['institution']

        database.save_profile(identity_id=session['primary_identity'],
                              name=name,
                              email=email,
                              institution=institution)

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

    client = load_portal_client()
    client.oauth2_start_flow(redirect_uri, refresh_tokens=True)

    # If there's no "code" query string parameter, we're in this route
    # starting a Globus Auth login flow.
    if 'code' not in request.args:
        additional_authorize_params = (
            {'signup': 1} if request.args.get('signup') else {})

        auth_uri = client.oauth2_get_authorize_url(
            additional_params=additional_authorize_params)

        return redirect(auth_uri)
    else:
        # If we do have a "code" param, we're coming back from Globus Auth
        # and can start the process of exchanging an auth code for a token.
        code = request.args.get('code')
        tokens = client.oauth2_exchange_code_for_tokens(code)

        id_token = tokens.decode_id_token(client)
        session.update(
            tokens=tokens.by_resource_server,
            is_authenticated=True,
            name=id_token.get('name', ''),
            email=id_token.get('email', ''),
            institution=id_token.get('institution', ''),
            primary_username=id_token.get('preferred_username'),
            primary_identity=id_token.get('sub'),
        )

        profile = database.load_profile(session['primary_identity'])

        if profile:
            name, email, institution = profile

            session['name'] = name
            session['email'] = email
            session['institution'] = institution
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

# def newProject():
#     VC3ClientAPI.defineProject()
#     flash('New project was successfully posted')
#     return redirect(url_for('show_projects'))

# def newProject():
#     if request.method == 'POST':
#         session['projectName'] == request.form['projectName']
#         session['projectScience'] == request.form['projectScience']
#         session['projectDescription'] == request.form['projectDescription']
#         flash('New Project was successfully posted')
#         return redirect(url_for('show_projects'))
#     return render_template('new.jinja2')

# def add_entry():
#     db = database.get_db()
#     db.execute('insert into entries (title, text) values (?, ?)',
#                [request.form['projectName'], request.form['text']])
#     db.commit()
#     flash('New project was successfully posted')
#     return redirect(url_for('show_entries'))


@app.route('/project/projectpages', methods=['GET', 'POST'])
@authenticated
def projectpages():
    return render_template('projects_pages.jinja2')


@app.route('/project', methods=['GET', 'POST'])
@authenticated
def project():
    return render_template('project.jinja2')

# def project():
#     if request.method == 'POST':
#         session['projectName'] == request.form['projectName']
#         session['projectScience'] == request.form['projectScience']
#         session['projectDescription'] == request.form['projectDescription']
#         return redirect(url_for('project'))
#     return render_template('new.jinja2')

# def show_projects():
#     projects = vc3client.listProjects()
#     return render_template('project.jinja2', projects=projects)

# def show_entries():
#     db = database.get_db()
#     cur = db.execute('select title, text from entries order by id desc')
#     entries = cur.fetchall()
#     return render_template('project.jinja2', entries=entries)


# @app.route('/project/<projectid>', methods=['GET', 'POST'])
# @authenticated
# def projectpages(projectid):
#     projectid = VC3ClientAPI.getProject()
#     return render_template('projects_pages.jinja2', projectid=projectid)


@app.route('/allocation', methods=['GET', 'POST'])
@authenticated
def allocation():
    return render_template('allocation.jinja2')


@app.route('/allocation/new', methods=['GET', 'POST'])
@authenticated
def new_allocation():
    return render_template('new_allocation.jinja2')


@app.route('/dashboard', methods=['GET', 'POST'])
@authenticated
def dashboard():
    return render_template('dashboard.jinja2')
