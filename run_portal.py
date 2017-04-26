#!/usr/bin/env python

import sys

from portal import app

# Import CherryPy
import cherrypy
from cherrypy import wsgiserver

if __name__ == '__main__':
    # workaround for now
    d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
    server = wsgiserver.CherryPyWSGIServer(('www-dev.virtualclusters.org', 8080), d)
    try:
        server.start()
    except KeyboardInterrupt:
        server.stop()
    sys.exit(0)

    # Mount the application
    cherrypy.tree.graft(app, "/")

    # Unsubscribe the default server
    cherrypy.server.unsubscribe()

    # Instantiate a new server object
    server = cherrypy._cpserver.Server()

    # Configure the server object
    # server.socket_host = "192.170.227.145"
    server.socket_host = "www-dev.virtualclusters.org"
    server.socket_port = 8080
    server.thread_pool = 30

    # Subscribe this server
    server.subscribe()

    # Enable debugging
    cherrypy.config.update({
        'engine.autoreload_on': True,
        'log.screen': True,
        'server.socket_port': 8080,
        'server.socket_host': "www-dev.virtualclusters.org"
    })
    app.debug = True
    # Start the server engine (Option 1 *and* 2)
    cherrypy.engine.start()
    cherrypy.engine.block()

    # app.run(host='localhost', ssl_context=('./ssl/server.crt', './ssl/server.key'))
