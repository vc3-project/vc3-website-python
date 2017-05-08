from flask import Flask
import json
from flask_flatpages import FlatPages
from flask_frozen import Freezer

from portal.database import Database

__author__ = 'Jeremy Van <jeremyvan@uchicago.edu>'


app = Flask(__name__)
app.config.from_pyfile('portal.conf')
pages = FlatPages(app)
freezer = Freezer(app)

database = Database(app)

with open(app.config['DATASETS']) as f:
    datasets = json.load(f)


import portal.views
