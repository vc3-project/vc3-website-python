from flask import Flask
from flask_flatpages import FlatPages
from flask_frozen import Freezer
import logging.handlers
import logging

from vc3client import client
from ConfigParser import SafeConfigParser
from flaskext.markdown import Markdown

__author__ = 'Jeremy Van <jeremyvan@uchicago.edu>'


app = Flask(__name__)
app.config.from_pyfile('portal.conf')
app.config['TEMPLATES_AUTO_RELOAD'] = True

# set up logging
handler = logging.handlers.RotatingFileHandler(
    filename=app.config['VC3_WEBSITE_LOGFILE'])
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
handler.setFormatter(formatter)

pages = FlatPages(app)
freezer = Freezer(app)
Markdown(app)


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

app.jinja_env.globals.update(get_vc3_client=get_vc3_client)

# need to put this here since views uses the app object
import portal.views
import portal.rest_api
