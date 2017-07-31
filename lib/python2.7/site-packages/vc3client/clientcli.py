#!/usr/bin/env python
__author__ = "John Hover"
__copyright__ = "2017 John Hover"
__credits__ = []
__license__ = "GPL"
__version__ = "0.9.1"
__maintainer__ = "John Hover"
__email__ = "jhover@bnl.gov"
__status__ = "Production"

import argparse
import base64
import logging
import os
import sys
import traceback

from ConfigParser import ConfigParser
from client import VC3ClientAPI
from vc3infoservice.infoclient import  InfoMissingPairingException, InfoConnectionFailure

class VC3ClientCLI(object):
    '''
    
    '''
    def __init__(self):
        self.parseopts()
        self.setuplogging()

    def parseopts(self):
        parser = argparse.ArgumentParser()
        parser.add_argument('-c', '--config', 
                            action="store", 
                            dest='configpath', 
                            default='~/vc3-services/etc/vc3-client.conf', 
                            help='configuration file path.')
        
        parser.add_argument('-d', '--debug', 
                            action="store_true", 
                            dest='debug', 
                            help='debug logging')        

        parser.add_argument('-v', '--verbose', 
                            action="store_true", 
                            dest='verbose', 
                            help='verbose/info logging')            
        
        # Init sub-command
        ########################### User ##########################################
        subparsers = parser.add_subparsers( dest="subcommand")

        parser_usercreate = subparsers.add_parser('user-create', 
                                                help='create new vc3 user')
        parser_usercreate.add_argument('username', 
                                     action="store")
        
        parser_usercreate.add_argument('--firstname', 
                                     action="store", 
                                     dest="firstname", 
                                     default='unknown')

        parser_usercreate.add_argument('--lastname', 
                                     action="store", 
                                     dest="lastname", 
                                     default='unknown')

        parser_usercreate.add_argument('--email', 
                                     action="store", 
                                     dest="email", 
                                     default='unknown')

        parser_usercreate.add_argument('--institution', 
                                     action="store", 
                                     dest="institution", 
                                     default='unknown')     
        
        parser_userlist = subparsers.add_parser('user-list', 
                                                help='list vc3 user(s)')
        
        parser_userlist.add_argument('--username', 
                                     action="store")

        ########################### Project ##########################################
        parser_projectcreate = subparsers.add_parser('project-create', 
                                                help='create new vc3 project')
        
        parser_projectcreate.add_argument('projectname', 
                                     action="store")

        parser_projectcreate.add_argument('--owner', 
                                     action="store", 
                                     dest="owner", 
                                     default='unknown')

        parser_projectcreate.add_argument('--members', 
                                     action="store", 
                                     dest="members", 
                                     default=None,
                                     help='comma-separated list of vc3users'
                                     )

        parser_projectadduser = subparsers.add_parser('project-adduser', 
                                                help='add user to vc3 project')
        
        parser_projectadduser.add_argument('project', 
                                     action="store")

        parser_projectadduser.add_argument('user', 
                                     action="store", 
                                     )
              
        
        parser_projectlist = subparsers.add_parser('project-list', 
                                                help='list all vc3 project(s)')

        parser_projectlist.add_argument('--projectname', 
                                     action="store",
                                     dest='projectname',
                                     required=False, 
                                     help='list details of specified project',
                                     default=None)

        ########################### Resource ##########################################
        parser_resourcecreate = subparsers.add_parser('resource-create', 
                                                help='create new vc3 resource')
        
        parser_resourcecreate.add_argument('resourcename',
                                           action="store")

        parser_resourcecreate.add_argument('--owner', 
                                     action="store", 
                                     dest="owner", 
                                    )

        parser_resourcecreate.add_argument('--accesstype', 
                                     action="store", 
                                     dest="accesstype",
                                     help="grid|remote-batch|local-batch|cloud", 
                                     )

        parser_resourcecreate.add_argument('--accessmethod', 
                                     action="store", 
                                     dest="accessmethod",
                                     help="ce|ssh|gsissh|local", 
                                     )

        parser_resourcecreate.add_argument('--accessflavor', 
                                     action="store", 
                                     dest="accessflavor",
                                     help="condor-ce|slurm|sge|ec2|nova|gce",  
                                     )

        parser_resourcecreate.add_argument('--gridresource', 
                                     action="store", 
                                     dest="gridresource",
                                     help="e.g. http://cldext02.usatlas.bnl.gov:8773/services/Cloud, corigrid.nersc.gov/jobmanager-slurm ",  
                                     default=None
                                     )

        parser_resourcecreate.add_argument('--mfa', 
                                     action="store_true", 
                                     dest="mfa",
                                     help="requires multi-factor/OTP authentication",
                                     default=False, 
                                     )        
                                        
                                        
        parser_resourcelist = subparsers.add_parser('resource-list', 
                                                help='list vc3 resource(s)')

        parser_resourcelist.add_argument('--resource',
                                         dest='resourcename', 
                                         action="store",
                                         required=False, 
                                         help='list details of specified resource',
                                         default=None)

        ########################### Allocation  ##########################################
        parser_allocationcreate = subparsers.add_parser('allocation-create', 
                                                help='create new vc3 allocation')
        
        parser_allocationcreate.add_argument('allocationname', 
                                     action="store")

        parser_allocationcreate.add_argument('--owner', 
                                     action="store", 
                                     dest="owner", 
                                     )

        parser_allocationcreate.add_argument('--resource', 
                                     action="store", 
                                     dest="resource", 
                                     )

        parser_allocationcreate.add_argument('--accountname', 
                                     action="store", 
                                     dest="accountname", 
                                     )        
        
    
        
        parser_allocationlist = subparsers.add_parser('allocation-list', 
                                                help='list vc3 allocation(s)')

        parser_allocationlist.add_argument('--allocationname', 
                                         action="store",
                                         required=False, 
                                         help='list details of specified allocation',
                                         default=None)


        ########################### Nodes  ##########################################
        
        
        
        
        
        ########################### Cluster  ##########################################
        parser_cluster = subparsers.add_parser('cluster-create', 
                help='create new cluster specification')

        parser_cluster.add_argument('clustername', 
                help='name of the cluster to be created',
                action="store")


        
        




        ########################### Environment  ##########################################
        parser_environ = subparsers.add_parser('environment-create', 
                help='create new environment')

        parser_environ.add_argument('environmentname', 
                help='name of the environment to be created',
                action="store")

        parser_environ.add_argument('--owner',
                action="store", 
                dest="owner", 
                default='unknown')

        parser_environ.add_argument('--packages', 
                action='store', 
                dest='packages', 
                default='',
                help='comma separated list of packages to be installed'
                )

        parser_environ.add_argument('--filesmap', 
                action='store', 
                dest='filesmap', 
                default='',
                help='comma separated list of LOCAL=REMOTE file name specifications'
                )

        parser_environ.add_argument('--envmap', 
                action='store', 
                dest='envmap', 
                default='',
                help='[[[ lacks documentation ]]]'
                )

        
        parser_environmentlist = subparsers.add_parser('environment-list', 
                                                help='list vc3 environment(s)')

        parser_environmentlist.add_argument('--environmentname', 
                                         action="store",
                                         required=False, 
                                         help='list details of specified environment',
                                         default=None)
        
        ########################### Request  ##########################################
        parser_request = subparsers.add_parser('request-create', 
                help='create new request specification')

        parser_request.add_argument('requestname', 
                                    help='name of the request to be created',
                                    action="store")

        parser_request.add_argument('--expiration', 
                action='store', 
                dest='expiration', 
                help='Date YYYY-MM-DD,HH:MM:SS at which this request expires',
                default=None
                )

        
        parser_request.add_argument('--allocations', 
                action='store', 
                dest='allocations', 
                help='comma separated list of allocations to be used by the request',
                default=None
                )

        parser_request.add_argument('--environments', 
                action='store', 
                dest='environments', 
                help='Environment to be installed on top of the request',
                default=None
                )

        parser_request.add_argument('--policy', 
                action='store', 
                dest='policy', 
                help='Policy for using the allocations',
                default='static-balanced')

        ########################### Pairing  ##########################################
        parser_pairingcreate = subparsers.add_parser('pairing-create', 
                                                help='create new pairing request')
        
        parser_pairingcreate.add_argument('commonname',
                                           action="store",
                                           help='SSL Subject Common Name (CN); a vc3 username or hostname'            
                                           )

        parser_pairingretrieve = subparsers.add_parser('pairing-retrieve', 
                                                help='Get cert and key for a pairing request')
        
        parser_pairingretrieve.add_argument('pairingcode',
                                           action="store",
                                           help="unique pairing code from original request")       
        
        parser_pairingretrieve.add_argument('--certfile', 
                                     action="store", 
                                     dest="certfile", 
                                     help="path/filename to write SSL certificate",
                                     default=None
                                     ) 
        
        parser_pairingretrieve.add_argument('--keyfile', 
                                     action="store", 
                                     dest="keyfile", 
                                     help="path/filename to write SSL key",
                                     default=None
                                     )        

        ############################################################          
        self.results= parser.parse_args()



    def setuplogging(self):
        self.log = logging.getLogger()
        FORMAT='%(asctime)s (UTC) [ %(levelname)s ] %(name)s %(filename)s:%(lineno)d %(funcName)s(): %(message)s'
        formatter = logging.Formatter(FORMAT)
        #formatter.converter = time.gmtime  # to convert timestamps to UTC
        logStream = logging.StreamHandler()
        logStream.setFormatter(formatter)
        self.log.addHandler(logStream)
    
        self.log.setLevel(logging.WARN)
        if self.results.debug:
            self.log.setLevel(logging.DEBUG)
        if self.results.verbose:
            self.log.setLevel(logging.INFO)
        self.log.info('Logging initialized.')


    def run(self):
        cp = ConfigParser()
        ns = self.results
        self.log.info("Config is %s" % ns.configpath)
        cp.read(os.path.expanduser(ns.configpath))

        capi = VC3ClientAPI(cp)
        
        # User commands
        if ns.subcommand == 'user-create':
            u = capi.defineUser( ns.username,
                                 ns.firstname,
                                 ns.lastname,
                                 ns.email,
                                 ns.institution)
            self.log.debug("User is %s" % u)
            capi.storeUser(u)
            
        elif ns.subcommand == 'user-list' and ns.username is None:
            ulist = capi.listUsers()
            for u in ulist:
                print(u)
        
        elif ns.subcommand == 'user-list' and ns.username is not None:
            uo = capi.getUser(ns.username)
            print(uo)
        
        # Project commands
        elif ns.subcommand == 'project-create':
            if ns.members is not None:
                memberslist = ns.members.split(',')
                
            p = capi.defineProject( ns.projectname,
                                    ns.owner,
                                    memberslist )
            self.log.debug("Project is %s" % p)
            capi.storeUser(p)    
            
        elif ns.subcommand == 'project-list' and ns.projectname is None:
            plist = capi.listProjects()
            for p in plist:
                print(p)
        
        elif ns.subcommand == 'project-list' and ns.projectname is not None:
            po = capi.getProject(ns.projectname)
            print(po)

        elif ns.subcommand == 'project-adduser':
            po = capi.getProject(ns.project)
            po.addUser(ns.user)
            capi.storeProject(po)
            
        # Resource commands
        elif ns.subcommand == 'resource-create':
            r = capi.defineResource( ns.resourcename,
                                     ns.owner,
                                     ns.accesstype,
                                     ns.accessmethod,
                                     ns.accessflavor,
                                     ns.gridresource,
                                     ns.mfa )
            self.log.debug("Resource is %s" % r)
            capi.storeResource(r)    
            
        elif ns.subcommand == 'resource-list' and ns.resourcename is None:
            rlist = capi.listResources()
            for r in rlist:
                print(r)
        
        elif ns.subcommand == 'resource-list' and ns.resourcename is not None:
            ro = capi.getResource(ns.resourcename)
            print(ro)
        
        
        # Allocation commands
        elif ns.subcommand == 'allocation-create':
            a = capi.defineAllocation( ns.allocationname,
                                       ns.owner,
                                       ns.resource,
                                       ns.accountname
                                       )
            self.log.debug("Allocation is %s" % a)
            capi.storeAllocation(a)    
            
        elif ns.subcommand == 'allocation-list' and ns.allocationname is None:
            alist = capi.listAllocations()
            for a in alist:
                print(a)
        
        elif ns.subcommand == 'allocation-list' and ns.allocationname is not None:
            ao = capi.getAllocation(ns.allocationname)
            print(ao)

        # Cluster create
        elif ns.subcommand == 'request-create':
            c = capi.defineCluster( ns.requestname,
                                    ns.allocations,
                                    ns.policy,
                                    ns.environments)
            self.log.debug("Cluster is %s" % c)
            capi.storeCluster(c)    

        


        # Environment create
        elif ns.subcommand == 'environment-create':
            filemap = ns.filesmap.split(',')
            files = {}
            for names in filemap:
                (local, remote) = names.split('=')
                local = os.path.expanduser(local)
                self.log.debug("Reading local file %s for remote %s" % (local, remote))
                with open(local, 'r') as l_f:
                    all = l_f.read()
                    files[remote] = VC3ClientAPI.encode(all)
                                
            e = capi.defineEnvironment( ns.environmentname,
                    ns.owner,
                    ns.packages.split(','),
                    files,
                    ns.envmap)
            self.log.debug("Environment is %s" % e)
            capi.storeEnvironment(e)
        
        elif ns.subcommand == 'environment-list' and ns.environmentname is None:
            elist = capi.listEnvironments()
            for e in elist:
                print(e)
        
        elif ns.subcommand == 'environment-list' and ns.environmentname is not None:
            eo = capi.getEnvironment(ns.environmentname)
            print(eo)
        
        
        
        
        # Pairing commands
        elif ns.subcommand == 'pairing-create':
            code = capi.requestPairing(ns.commonname)
            print(code)        
        
        elif ns.subcommand == 'pairing-retrieve':
            try:
                (cert, key) = capi.getPairing(ns.pairingcode)
                if ns.certfile is not None and ns.keyfile is not None:
                    certpath = os.path.expanduser(ns.certfile)
                    keypath = os.path.expanduser(ns.keyfile)
                    cf = open(certpath, 'w')
                    cf.write(cert)
                    cf.close()
                    
                    # Necessary to avoid security issues with world or group writable key file. 
                    if os.path.isfile(keypath):
                        os.remove(keypath)
                    original_umask = os.umask(0o177)  # 0o777 ^ 0o600
                    try:
                        kf = os.fdopen(os.open(keypath, os.O_WRONLY | os.O_CREAT, 0o600), 'w')
                    finally:
                        os.umask(original_umask)
                    kf.write(key)
                    kf.close()                
                    
                else:
                    # print cert, key to stdout  
                    print(cert)
                    print("")
                    print(key)
            except InfoMissingPairingException:
                print("Invalid pairing code or not satisfied yet. Try in 30 seconds.")   
        else:
            self.log.warning('Unrecognized subcommand is %s' % ns.subcommand)
            

if __name__ == '__main__':
    vc3cli = VC3ClientCLI()
    try:
        vc3cli.run()
    except Exception, e:
            print(traceback.format_exc(None))
            sys.exit(1) 
