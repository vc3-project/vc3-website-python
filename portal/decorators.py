from flask import redirect, request, session, url_for, flash
from functools import wraps
from portal.utils import get_vc3_client


def authenticated(fn):
    """Mark a route as requiring authentication."""
    @wraps(fn)
    def decorated_function(*args, **kwargs):
        if not session.get('is_authenticated'):
            return redirect(url_for('login', next=request.url))

        if request.path == '/logout':
            return fn(*args, **kwargs)

        if (not session.get('name') or
                not session.get('email') or
                not session.get('institution')) and request.path != '/profile':
            return redirect(url_for('show_profile_page', next=request.url))

        return fn(*args, **kwargs)
    return decorated_function


def allocation_validated(f):
    """Mark a route as requiring a validated allocation."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        vc3_client = get_vc3_client()
        allocations = vc3_client.listAllocations()
        for allocation in allocations:
            if (session['name'] == allocation.owner and
                    allocation.state == "ready"):
                return f(*args, **kwargs)
        flash('You must have a validated allocation to create a project.', 'warning')
        return redirect(url_for('list_allocations', next=request.url))
    return decorated_function


def project_exists(f):
    """Mark a route as requiring being within any validated project."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        vc3_client = get_vc3_client()
        projects = vc3_client.listProjects()
        for project in projects:
            if (session['name'] == project.owner or
                    session['name'] in project.members):
                return f(*args, **kwargs)
        flash('You must be within a project in order to proceed.', 'warning')
        return redirect(url_for('list_projects', next=request.url))
    return decorated_function
