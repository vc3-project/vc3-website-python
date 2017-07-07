from flask import Flask
import json
from flask_flatpages import FlatPages
from flask_frozen import Freezer

from portal.database import Database

# from configparser import ConfigParser
# from vc3_client.vc3client.client import VC3ClientAPI

__author__ = 'Jeremy Van <jeremyvan@uchicago.edu>'


app = Flask(__name__)
app.config.from_pyfile('portal.conf')
pages = FlatPages(app)
freezer = Freezer(app)

database = Database(app)

# cp = ConfigParser()
# cp.read('/vc3_client/etc/vc3-client.conf')
# vc3clientobj = VC3ClientAPI(cp)

with open(app.config['DATASETS']) as f:
    datasets = json.load(f)


import portal.views
