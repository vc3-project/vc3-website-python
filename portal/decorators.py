from flask import redirect, request, session, url_for
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
    vc3_client = get_vc3_client()
    allocations = vc3_client.listAllocations()

    @wraps(f)
    def decorated_function(*args, **kwargs):
        for allocation in allocations:
            if (not session['name'] == allocation.owner and
                    not allocation.state == "validated"):
                return redirect(url_for('create_allocation', next=request.url))
            return f(*args, **kwargs)
    return decorated_function
