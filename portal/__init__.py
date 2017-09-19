from flask import Flask
import json
from flask_flatpages import FlatPages
from flask_frozen import Freezer
from portal.database import Database
import logging.handlers

__author__ = 'Jeremy Van <jeremyvan@uchicago.edu>'


app = Flask(__name__)
app.config.from_pyfile('portal.conf')
app.config['TEMPLATES_AUTO_RELOAD'] = True

# set up logging
handler = logging.handlers.RotatingFileHandler(filename="/tmp/vc3-website-exceptions.logs")
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)

pages = FlatPages(app)
freezer = Freezer(app)

# need to put this here since views uses the app object
import portal.views
