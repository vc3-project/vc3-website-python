#!/usr/bin/env python

import sys
import logging

from portal import app


handler = logging.handlers.RotatingFileHandler(filename="/tmp/vc3.logs")
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)
app.logger.info('Info')

logger = logging.getLogger()
logger.addHandler(handler)

if __name__ == "__main__":
     app.run(host='localhost')
