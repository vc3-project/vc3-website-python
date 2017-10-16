from flask import Flask
from flask_flatpages import FlatPages
from flask_frozen import Freezer
import logging.handlers
import logging

__author__ = 'Jeremy Van <jeremyvan@uchicago.edu>'


app = Flask(__name__)
app.config.from_pyfile('portal.conf')
app.config['TEMPLATES_AUTO_RELOAD'] = True

# set up logging
handler = logging.handlers.RotatingFileHandler(filename=app.config['VC3_WEBSITE_LOGFILE'])
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)
formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')
handler.setFormatter(formatter)

pages = FlatPages(app)
freezer = Freezer(app)

# need to put this here since views uses the app object
import portal.views
import portal.rest_api
