#!/usr/bin/env python

import sys

from portal import app, freezer

# Import CherryPy

# import cherrypy
# from cherrypy import wsgiserver

if __name__ == "__main__":
<<<<<<< HEAD
    # # workaround for now
    # d = wsgiserver.WSGIPathInfoDispatcher({'/': app})
    # server = wsgiserver.CherryPyWSGIServer(('www-dev.virtualclusters.org', 8080), d)
    #
    # try:
    #     server.start()
    # except KeyboardInterrupt:
    #     server.stop()
    # sys.exit(0)
    #
    # # Mount the application
    # cherrypy.tree.graft(app, "/")
    #
    # # Unsubscribe the default server
    # cherrypy.server.unsubscribe()
    #
    # # Instantiate a new server object
    # server = cherrypy._cpserver.Server()
    #
    # # Configure the server object
    # # server.socket_host = "192.170.227.145"
    # server.socket_host = "www-dev.virtualclusters.org"
    # server.socket_port = 8080
    # server.thread_pool = 30
    #
    # # Subscribe this server
    # server.subscribe()
=======
    workaround for now
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
        'engine.autoreload.on': True,
        'log.screen': True,
        # 'log.error_file': 'Web.log',
        # 'log.access_file': 'Access.log',
        'server.socket_port': 8080,
        'server.socket_host': "www-dev.virtualclusters.org"
    })
    app.debug = True
    # Start the server engine (Option 1 *and* 2)
    cherrypy.engine.start()
    cherrypy.engine.block()
>>>>>>> b334dbd2ef122f151987e360af69320ddfd637c3
    #
    # # Enable debugging
    # cherrypy.config.update({
    #     'engine.autoreload.on': True,
    #     'log.screen': True,
    #     # 'log.error_file': 'Web.log',
    #     # 'log.access_file': 'Access.log',
    #     'server.socket_port': 8080,
    #     'server.socket_host': "www-dev.virtualclusters.org"
    # })
    # app.debug = True
    # # Start the server engine (Option 1 *and* 2)
    # cherrypy.engine.start()
    # cherrypy.engine.block()

    if len(sys.argv) > 1 and sys.argv[1] == "build":
        freezer.freeze()
    else:
        app.run(host='localhost', ssl_context=('./ssl/server.crt', './ssl/server.key'))
