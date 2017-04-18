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
    server.socket_host = "0.0.0.0"
    server.socket_port = 8080
    server.thread_pool = 30

    app.run(host='localhost', ssl_context=('./ssl/server.crt', './ssl/server.key'))
