#! /usr/bin/env python
__author__ = "John Hover, Jose Caballero"
__copyright__ = "2017 John Hover"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.1"
__maintainer__ = "John Hover"
__email__ = "jhover@bnl.gov"
__status__ = "Production"


import cherrypy
import logging
import logging.handlers
import os
import platform
import pwd
import random
import json
import string
import socket
import sys
import threading
import time
import traceback

from optparse import OptionParser
from ConfigParser import ConfigParser


# Since script is in package "vc3" we can know what to add to path for 
# running directly during development
(libpath,tail) = os.path.split(sys.path[0])
sys.path.append(libpath)

import pluginmanager as pm

class InfoHandler(object):
    '''
    Handles low-level operations and persistence of information 
    from service using back-end plugin.
    
    Data at this level is converted to/from native Python objects for storage/retrieval
     
    '''
    def __init__(self, config):
        self.log = logging.getLogger()
        self.log.debug("Initializing Info Handler...")
        self.config = config
        
        # Get persistence plugin
        pluginname = config.get('persistence','plugin')
        psect = "plugin-%s" % pluginname.lower()
        self.log.debug("Creating persistence plugin...")
        self.persist = pm.getplugin(parent=self, 
                                    paths=['vc3infoservice', 'plugins', 'persist'], 
                                    name=pluginname, 
                                    config=self.config, 
                                    section=psect)
        self.log.debug("Done initting InfoHandler")

    def storedocument(self, key, doc):
        self.log.debug("Storing document for key %s" % key)
        pd = json.loads(doc)
        self.persist.storedocument(key, pd)
   
    def mergedocument(self, key, doc):
        self.log.debug("input doc to merge is type %s" % type(doc))
        dcurrent = self.persist.getdocument(key)
        self.log.debug("current retrieved doc is type %s" % type(dcurrent))
        md = json.loads(doc)
        self.log.debug("doc to merge is type %s" % type(md))
        newdoc = self.merge( md, dcurrent)
        self.log.debug("Merging document for key %s" % key)
        self.persist.storedocument(key, newdoc)
    
    def getdocument(self, key):
        '''
        Gets JSON representation of document. 
        '''
        pd = self._getpythondocument(key)
        jd = json.dumps(pd)
        self.log.debug("d is type %s" % type(jd))
        return jd

    def _getpythondocument(self, key):
        '''
        Gets Python object. 
        '''
        d = self.persist.getdocument(key)
        self.log.debug("d is type %s with value %s" % (type(d), d))
        return d
    
    def _storepythondocument(self, key, pd):
        self.log.debug("Storing document for key %s" % key)
        self.persist.storedocument(key, pd)
    
    
    def deletesubtree(self, path):
        lst = path.split('.')
        try:
            self.persist.deletesubtree(lst)
        except IndexError:
            raise Exception('path should have more than one key')

    def merge(self, source, destination):
        """
        merges nested python dictionaries.
        run me with nosetests --with-doctest file.py
    
        >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
        >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
        >>> merge(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
        True
        """
        self.log.debug("source is type %s" % type(source))
        self.log.debug("destination is type %s" % type(destination))
        for key, value in source.items():
            self.log.debug("processing node %s" % key)
            if isinstance(value, dict):
                # get node or create one
                node = destination.setdefault(key, {})
                self.merge(value, node)
            else:
                destination[key] = value
        return destination

    ##################################################################################
    #   Pairing-related calls. 
    ##################################################################################
    
    def getpairing(self, key, pairingcode):
        '''
        Pull pairing document, check each entry to see if <entry>.pairingcode = pairingcode.
        If so, and cert and key are not none, prepare to return them, delete entry, return Pairing
        '''
        failmsg="Invalid pairing code or not satisfied yet. Try in 30 seconds."
        prd = None
        pd = self._getpythondocument(key)
        self.log.debug("Received dict: %s" % pd)
        try:        
            self.log.debug("Entries are %s" % pd[key] )
            for p in pd[key].keys():
                self.log.debug("Checking entry %s for pairingcode..." % p)
                if pd[key][p]['pairingcode'] == pairingcode:
                    self.log.debug("Found matching entry %s value %s" % (p, pd[key][p]))
                    if pd[key][p]['cert'] is not None:
                        prd = json.dumps(pd[key][p])
                        try:
                            self.log.debug("Attempting to delete entry %s from pairing." % p)
                            pd[key].pop(p, None)
                            self.log.debug("Deleted entry %s from pairing. Re-storing.." % p)
                        except KeyError:
                            self.log.warning("Failed to delete entry %s from pairing." % p)
                        self._storepythondocument(key, pd)
                    else:
                        self.log.info("Certificate for requested pairing not generated yet.")
            self.log.debug("Returning pairing entry JSON %s" % prd)
            if prd is None:
                cherrypy.response.headers["Status"] = "404"
                return failmsg
            return prd
        except KeyError:
            cherrypy.response.headers["Status"] = "404"
            return failmsg
   
   

class InfoRoot(object):

    @cherrypy.expose
    def index(self):
        return "Nothing to see. Go to /info"    

    @cherrypy.expose
    def generate(self, length=8):
        return ''.join(random.sample(string.hexdigits, int(length)))

class InfoServiceAPI(object):
    ''' 
        Data at this level is assumed to be  JSON text/plain.
    '''
    exposed = True 
    
    def __init__(self, config):
        self.log = logging.getLogger()
        self.log.debug("Initting InfoServiceAPI...")
        self.infohandler = InfoHandler(config)
        self.log.debug("InfoServiceAPI init done." )
    
    def GET(self, key, pairingcode=None):
        if pairingcode is None:
            d = self.infohandler.getdocument(key) 
            self.log.debug("Document retrieved for key %s with val %s" % (key,d))
            return d
        else:
            self.log.debug("Handling pairing retrieval")
            d = self.infohandler.getpairing(key, pairingcode)
            self.log.debug("Pairing retrieved for code %s with val %s" % (pairingcode,d))
            return d

    @cherrypy.tools.accept(media='text/plain')
    def PUT(self, key, data):
        self.log.debug("Storing document %s" % data)
        self.infohandler.mergedocument(key, data)
        self.log.debug("Document stored for key %s" % key)
        return "Document stored for key %s\n" % key
        
    def POST(self, key, data):
        self.log.debug("Storing document %s" % data)
        self.infohandler.storedocument(key, data)
        self.log.debug("Document stored for key %s" % key)
        return "Document stored for key %s\n" % key
        
    def DELETE(self, key, name):
        '''
        Unusual call that operates on node provided in path only. Path expressed as node 'name' attribute. 
        /info/<key>/<name>/
        Deletion only occurs if identity is allowed delete by ACL at <name>: { 'acl' :<acl> } 
        '''

        self.log.debug("Deleting subtree %s" % name)
        self.infohandler.deletesubtree(name)
        self.log.debug("Subtree deleted at %s" % name)
        return "Subtree deleted at %s" % name


    def stripquotes(self,s):
        rs = s.replace("'","")
        return rs


class InfoService(object):
    
    def __init__(self, config):
        self.log = logging.getLogger()
        self.log.debug('InfoService class init...')
        self.config = config
        self.certfile = os.path.expanduser(config.get('netcomm','certfile'))
        self.keyfile = os.path.expanduser(config.get('netcomm', 'keyfile'))
        self.chainfile = os.path.expanduser(config.get('netcomm','chainfile'))
        self.httpport = int(config.get('netcomm','httpport'))
        self.httpsport = int(config.get('netcomm','httpsport'))
        self.sslmodule = config.get('netcomm','sslmodule')
        
        self.log.debug("certfile=%s" % self.certfile)
        self.log.debug("keyfile=%s" % self.keyfile)
        self.log.debug("chainfile=%s" % self.chainfile)
        
        self.log.debug('InfoService class done.')
        
    def run(self):
        self.log.debug('Infoservice running...')
          
        cherrypy.tree.mount(InfoRoot())
        cherrypy.tree.mount(InfoServiceAPI(self.config),'/info',
                                {'/':
        {'request.dispatch': cherrypy.dispatch.MethodDispatcher()}
    })
        #cherrypy.tree.mount(InfoServiceAPI(self.config))
        
        
        cherrypy.server.unsubscribe()
    
        server1 = cherrypy._cpserver.Server()
        server1.socket_port=self.httpsport
        server1._socket_host='0.0.0.0'
        server1.thread_pool=30
        server1.ssl_module = self.sslmodule
        server1.ssl_certificate = self.certfile
        server1.ssl_private_key = self.keyfile
        server1.ssl_certificate_chain = self.chainfile
        server1.subscribe()
    
        #server2 = cherrypy._cpserver.Server()
        #server2.socket_port=self.httpport
        #server2._socket_host="0.0.0.0"
        #server2.thread_pool=30
        #server2.subscribe()
    
        cherrypy.engine.start()
        cherrypy.engine.block()   
    

class InfoServiceCLI(object):
    """class to handle the command line invocation of service. 
       parse the input options,
       setup everything, and run InfoService class
    """
    def __init__(self):
        self.options = None 
        self.args = None
        self.log = None
        self.config = None

        self.__presetups()
        self.__parseopts()
        self.__setuplogging()
        self.__platforminfo()
        self.__checkroot()
        self.__createconfig()

    def __presetups(self):
        '''
        we put here some preliminary steps that 
        for one reason or another 
        must be done before anything else
        '''

    
    def __parseopts(self):
        parser = OptionParser(usage='''%prog [OPTIONS]
vc3-info-service is a information store for VC3

This program is licenced under the GPL, as set out in LICENSE file.

Author(s):
John Hover <jhover@bnl.gov>
''', version="%prog $Id: infoservice.py 1-13-17 23:58:06Z jhover $" )

        parser.add_option("-d", "--debug", 
                          dest="logLevel", 
                          default=logging.WARNING,
                          action="store_const", 
                          const=logging.DEBUG, 
                          help="Set logging level to DEBUG [default WARNING]")
        parser.add_option("-v", "--info", 
                          dest="logLevel", 
                          default=logging.WARNING,
                          action="store_const", 
                          const=logging.INFO, 
                          help="Set logging level to INFO [default WARNING]")
        parser.add_option("--console", 
                          dest="console", 
                          default=False,
                          action="store_true", 
                          help="Forces debug and info messages to be sent to the console")
        parser.add_option("--quiet", dest="logLevel", 
                          default=logging.WARNING,
                          action="store_const", 
                          const=logging.WARNING, 
                          help="Set logging level to WARNING [default]")

        default_conf = "/etc/vc3/vc3-infoservice.conf"
        if 'VC3_SERVICES_HOME' in os.environ:
            default_conf = os.path.join(os.environ['VC3_SERVICES_HOME'], 'etc', 'vc3-infoservice.conf') + ',' + default_conf

        parser.add_option("--conf", dest="confFiles", 
                          default=default_conf,
                          action="store", 
                          metavar="FILE1[,FILE2,FILE3]", 
                          help="Load configuration from FILEs (comma separated list)")

        parser.add_option("--log", dest="logfile", 
                          default="stdout", 
                          metavar="LOGFILE", 
                          action="store", 
                          help="Send logging output to LOGFILE or SYSLOG or stdout [default <syslog>]")
        parser.add_option("--runas", dest="runAs", 
                          #
                          # By default
                          #
                          default=pwd.getpwuid(os.getuid())[0],
                          action="store", 
                          metavar="USERNAME", 
                          help="If run as root, drop privileges to USER")
        (self.options, self.args) = parser.parse_args()

        self.options.confFiles = self.options.confFiles.split(',')

    def __setuplogging(self):
        """ 
        Setup logging 
        """
        self.log = logging.getLogger()
        if self.options.logfile == "stdout":
            logStream = logging.StreamHandler()
        else:
            lf = os.path.expanduser(self.options.logfile)
            logdir = os.path.dirname(lf)
            if not os.path.exists(logdir):
                os.makedirs(logdir)
            runuid = pwd.getpwnam(self.options.runAs).pw_uid
            rungid = pwd.getpwnam(self.options.runAs).pw_gid                  
            os.chown(logdir, runuid, rungid)
            logStream = logging.FileHandler(filename=lf)    

        # Check python version 
        major, minor, release, st, num = sys.version_info
        if major == 2 and minor == 4:
            FORMAT='%(asctime)s (UTC) [ %(levelname)s ] %(name)s %(filename)s:%(lineno)d : %(message)s'
        else:
            FORMAT='%(asctime)s (UTC) [ %(levelname)s ] %(name)s %(filename)s:%(lineno)d %(funcName)s(): %(message)s'
        formatter = logging.Formatter(FORMAT)
        formatter.converter = time.gmtime  # to convert timestamps to UTC
        logStream.setFormatter(formatter)
        self.log.addHandler(logStream)

        # adding a new Handler for the console, 
        # to be used only for DEBUG and INFO modes. 
        if self.options.logLevel in [logging.DEBUG, logging.INFO]:
            if self.options.console:
                console = logging.StreamHandler(sys.stdout)
                console.setFormatter(formatter)
                console.setLevel(self.options.logLevel)
                self.log.addHandler(console)
        self.log.setLevel(self.options.logLevel)
        self.log.info('Logging initialized at level %s.' % self.options.logLevel)


    def _printenv(self):

        envmsg = ''        
        for k in sorted(os.environ.keys()):
            envmsg += '\n%s=%s' %(k, os.environ[k])
        self.log.debug('Environment : %s' %envmsg)


    def __platforminfo(self):
        '''
        display basic info about the platform, for debugging purposes 
        '''
        self.log.info('platform: uname = %s %s %s %s %s %s' %platform.uname())
        self.log.info('platform: platform = %s' %platform.platform())
        self.log.info('platform: python version = %s' %platform.python_version())
        self._printenv()

    def __checkroot(self): 
        """
        If running as root, drop privileges to --runas' account.
        """
        starting_uid = os.getuid()
        starting_gid = os.getgid()
        starting_uid_name = pwd.getpwuid(starting_uid)[0]

        hostname = socket.gethostname()
        
        if os.getuid() != 0:
            self.log.info("Already running as unprivileged user %s at %s" % (starting_uid_name, hostname))
            
        if os.getuid() == 0:
            try:
                runuid = pwd.getpwnam(self.options.runAs).pw_uid
                rungid = pwd.getpwnam(self.options.runAs).pw_gid
                os.chown(self.options.logfile, runuid, rungid)
                
                os.setgid(rungid)
                os.setuid(runuid)
                os.seteuid(runuid)
                os.setegid(rungid)

                self._changehome()
                self._changewd()

                self.log.info("Now running as user %d:%d at %s..." % (runuid, rungid, hostname))
                self._printenv()

            
            except KeyError, e:
                self.log.error('No such user %s, unable run properly. Error: %s' % (self.options.runAs, e))
                sys.exit(1)
                
            except OSError, e:
                self.log.error('Could not set user or group id to %s:%s. Error: %s' % (runuid, rungid, e))
                sys.exit(1)

    def _changehome(self):
        '''
        Set environment HOME to user HOME.
        '''
        runAs_home = pwd.getpwnam(self.options.runAs).pw_dir 
        os.environ['HOME'] = runAs_home
        self.log.debug('Setting up environment variable HOME to %s' %runAs_home)


    def _changewd(self):
        '''
        changing working directory to the HOME directory of the new user,
        '''
        runAs_home = pwd.getpwnam(self.options.runAs).pw_dir
        os.chdir(runAs_home)
        self.log.debug('Switching working directory to %s' %runAs_home)


    def __createconfig(self):
        """Create config, add in options...
        """
        if self.options.confFiles != None:
            try:
                self.config = ConfigParser()
                self.config.read(self.options.confFiles)
            except Exception, e:
                self.log.error('Config failure')
                sys.exit(1)
        
        #self.config.set("global", "configfiles", self.options.confFiles)
           
    def run(self):
        """
        Create Daemon and enter main loop
        """

        try:
            self.log.info('Creating Daemon and entering main loop...')
            infosrv = InfoService(self.config)
            infosrv.run()
            
        except KeyboardInterrupt:
            self.log.info('Caught keyboard interrupt - exitting')
            f.join()
            sys.exit(0)
        except ImportError, errorMsg:
            self.log.error('Failed to import necessary python module: %s' % errorMsg)
            sys.exit(1)
        except:
            self.log.error('''Unexpected exception!''')
            # The following line prints the exception to the logging module
            self.log.error(traceback.format_exc(None))
            print(traceback.format_exc(None))
            sys.exit(1)          

if __name__ == '__main__':
    iscli = InfoServiceCLI()
    iscli.run()

