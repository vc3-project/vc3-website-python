#!/usr/bin/env python


import time
from portal import app

app.logger.info('{0} Application started'.format(time.ctime()))

if __name__ == "__main__":
     app.run(host='localhost')
