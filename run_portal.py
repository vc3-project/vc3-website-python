#!/usr/bin/env python

from portal import app

# Import CherryPy
import cherrypy

if __name__ == '__main__':
    # Mount the application
    cherrypy.tree.graft(app, "/")

    # Unsubscribe the default server
    cherrypy.server.unsubscribe()

    # Instantiate a new server object
    server = cherrypy._cpserver.Server()

    # Configure the server object
    server.socket_host = "192.170.227.145"
    server.socket_port = 8080
    server.thread_pool = 30

    # Subscribe this server
    server.subscribe()

    # Start the server engine (Option 1 *and* 2)
    cherrypy.engine.start()
    cherrypy.engine.block()

    # app.run(host='server.socket_host', ssl_context=('./ssl/server.crt', './ssl/server.key'))
