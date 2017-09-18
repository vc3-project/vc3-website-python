#!/usr/bin/env python

import logging
import time
from portal import app


handler = logging.handlers.RotatingFileHandler(filename="/tmp/vc3.logs")
handler.setLevel(logging.DEBUG)
app.logger.addHandler(handler)
app.logger.info('{0} Application started'.format(time.ctime()))

logger = logging.getLogger()
logger.addHandler(handler)

if __name__ == "__main__":
     app.run(host='localhost')
