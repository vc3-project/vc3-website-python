from flask import redirect, request, session, url_for, flash
from threading import Lock
from ConfigParser import SafeConfigParser

import os
import errno

import globus_sdk

from vc3client import client

try:
    from urllib.parse import urlparse, urljoin
except ImportError:
    from urlparse import urlparse, urljoin

from cryptography import x509
from cryptography.hazmat.backends import default_backend
import datetime

from portal import app


def load_portal_client():
    """Create an AuthClient for the portal"""
    # return globus_sdk.ConfidentialAppAuthClient(
    #     app.config['PORTAL_CLIENT_ID'], app.config['PORTAL_CLIENT_SECRET'])
    return globus_sdk.ConfidentialAppAuthClient(
        app.config['PORTAL_CLIENT_ID'], app.config['PORTAL_CLIENT_SECRET'])


def is_safe_redirect_url(target):
    """https://security.openstack.org/guidelines/dg_avoid-unvalidated-redirects.html"""  # noqa
    host_url = urlparse(request.host_url)
    redirect_url = urlparse(urljoin(request.host_url, target))

    return redirect_url.scheme in ('http', 'https') and \
        host_url.netloc == redirect_url.netloc


def get_safe_redirect():
    """https://security.openstack.org/guidelines/dg_avoid-unvalidated-redirects.html"""  # noqa
    url = request.args.get('next')
    if url and is_safe_redirect_url(url):
        return url

    url = request.referrer
    if url and is_safe_redirect_url(url):
        return url

    return '/'


def get_portal_tokens(
        scopes=['openid', 'urn:globus:auth:scope:demo-resource-server:all']):
    """
    Uses the client_credentials grant to get access tokens on the
    Portal's "client identity."
    """
    with get_portal_tokens.lock:
        if not get_portal_tokens.access_tokens:
            get_portal_tokens.access_tokens = {}

        scope_string = ' '.join(scopes)

        client = load_portal_client()
        tokens = client.oauth2_client_credentials_tokens(
            requested_scopes=scope_string)

        # walk all resource servers in the token response (includes the
        # top-level server, as found in tokens.resource_server), and store the
        # relevant Access Tokens
        for resource_server, token_info in tokens.by_resource_server.items():
            get_portal_tokens.access_tokens.update({
                resource_server: {
                    'token': token_info['access_token'],
                    'scope': token_info['scope'],
                    'expires_at': token_info['expires_at_seconds']
                }
            })

        return get_portal_tokens.access_tokens


def get_vc3_client():
    """
    Return a VC3 client instance

    :return: VC3 client instance on success
    """
    c = SafeConfigParser()
    c.readfp(open(app.config['VC3_CLIENT_CONFIG']))

    try:
        client_api = client.VC3ClientAPI(c)
        return client_api
    except Exception as e:
        app.logger.error("Couldn't get vc3 client: {0}".format(e))
        raise


get_portal_tokens.lock = Lock()
get_portal_tokens.access_tokens = None


def project_validated(name):
    """
    Checks to see if user exists within specific project

    :param name: name of project to be checked
    :return: True if user exists in project or False otherwise
    """
    vc3_client = get_vc3_client()
    # Grab project by name
    project = vc3_client.getProject(projectname=name)

    # Checks to see if user is in project
    if (session['name'] in project.members or
            session['name'] == project.owner):
        return True
    else:
        return False


def project_in_vc(name):
    """
    Checks to see if user exists within specific project associated with VC

    :param name: name of VC to be checked
    :return: True if user exists in project or False otherwise
    """
    vc3_client = get_vc3_client()
    projects = vc3_client.listProjects()
    vc = vc3_client.getRequest(requestname=name)
    vc_owner_projects = []

    for project in projects:
        if vc.owner == project.owner:
            vc_owner_projects.append(project)

    for p in vc_owner_projects:
        if (session['name'] in p.members or session['name'] == p.owner):
            return True
        else:
            return False


def allocation_script_for_resource(allocation_name, output_path):
    """
    Writes to output_path a script that a user has to execute at a resource.
    The script copies the public ssh key that vc3 would use to communicate with
    the resource.

    :param allocation_name: name of the allocation on the resource
    :param output_path: name of the file to write the script.

    :return: None, raises exception on errors (OSError if file cannot be created, vc3infoservice.core.InfoEntityMissingException if allocation does not exists.)
    """

    vc3_client = get_vc3_client()
    allocation = vc3_client.getAllocation(allocation_name)
    pubkey = vc3_client.decode(allocation.pubtoken)
    dir_name = os.path.dirname(output_path)

    try:
        os.makedirs(dir_name, 0755)
    except OSError as e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise

    with open(output_path, 'w+b') as fh:
        script = """#! /bin/sh

PUBKEY="{}"
AUTHFILE=~/.ssh/authorized_keys

if [ ! -d ~/.ssh ]
then
    /bin/echo -n "Creating ~/.ssh directory... "
    if mkdir -m 0700 -p ~/.ssh
    then
        echo "done"
    else
        echo "error"
        exit 1
    fi
fi

if [ ! -f $AUTHFILE ]
then
    /bin/echo -n "Creating $AUTHFILE file... "
    if (umask 177; touch $AUTHFILE)
    then
        echo "done"
    else
        echo "error"
        exit 1
    fi
fi

/bin/echo -n "Copying public key to $AUTHFILE file... "

if /bin/grep -q "$PUBKEY" $AUTHFILE
then
    echo "key already in file."
elif /bin/echo "$PUBKEY" >> $AUTHFILE
then
    echo "done"
else
    echo "error"
    exit 1
fi

exit 0

""".format(pubkey)
        fh.write(script)

def get_proxy_expiration_time(proxystr, method):
    if method == 'gsissh':
        return get_proxy_expiration_time_gsissh(proxystr)
    elif method == 'sshproxy':
        return get_proxy_expiration_time_sshproxy(proxystr)
    else:
        return "None"

def get_proxy_expiration_time_gsissh(proxystr):
    try:
        cert = x509.load_pem_x509_certificate(proxystr, default_backend())
    except Exception as e:
        app.logger.error("Error while reading proxy {0}".format(e))
        return 'Could not read proxy expiration time'
        
    cert_expire = cert.not_valid_after
    now = datetime.datetime.utcnow()
    exp_time = cert_expire - now
    time_s = exp_time.total_seconds()
    expiration = "{hours} hours, {minutes} minutes and {seconds} seconds.".format(hours=int(time_s / 3600),
                                                                                  minutes=int(time_s % 3600 / 60),
                                                                                  seconds=int(time_s % 60))

    return expiration 

def get_proxy_expiration_time_sshproxy(proxystr):
    return "Not implementet yet"
