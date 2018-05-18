
import flask
import base64
from portal.utils import get_vc3_client

from portal import app
from portal.decorators import authenticated


@app.route('/rest/virtual_cluster/<name>', methods=['GET'])
@authenticated
def virtual_cluster(name):
    """
    Get information for a specified cluster and return
    it in as json or jsonp

    :return: json or jsonp status of cluster
    """
    result = {}
    vc3_client = get_vc3_client()
    virtual_clusters = vc3_client.listRequests()
    nodesets = vc3_client.listNodesets()
    for vc in virtual_clusters:
        if vc.name == name:
            sanitized_obj = {'name': vc.name,
                             'state': vc.state,
                             'cluster': vc.cluster,
                             'statusraw': vc.statusraw,
                             'statusinfo': vc.statusinfo,
                             'displayname': vc.displayname,
                             'description': vc.description,
                             'statereason': vc.state_reason,
                             'action': vc.action,
                             'headnode': vc.headnode}
            if vc.statusinfo is not None:
                sanitized_obj['statusinfo_error'] = vc.statusinfo[vc.cluster]['error']
                sanitized_obj['statusinfo_idle'] = vc.statusinfo[vc.cluster]['idle']
                sanitized_obj['statusinfo_node_number'] = vc.statusinfo[vc.cluster]['node_number']
                sanitized_obj['statusinfo_requested'] = vc.statusinfo[vc.cluster]['requested']
                sanitized_obj['statusinfo_running'] = vc.statusinfo[vc.cluster]['running']
            for nodeset in nodesets:
                if nodeset.name == vc.headnode:
                    sanitized_obj['headnode_app_host'] = nodeset.app_host
                    sanitized_obj['headnode_state'] = nodeset.state
                    sanitized_obj['headnode_state_reason'] = nodeset.state_reason

            return flask.jsonify(sanitized_obj)
    return flask.jsonify(result), 404


@app.route('/rest/allocation/<name>', methods=['GET'])
@authenticated
def allocation(name):
    """
    Get information for a specified cluster and return
    it in as json or jsonp

    :return: json or jsonp status of cluster
    """
    result = {}
    vc3_client = get_vc3_client()
    allocations = vc3_client.listAllocations()
    for x in allocations:
        if x.name == name:
            sanitized_obj = {'name': x.name,
                             'state': x.state,
                             'action': x.action,
                             'owner': x.owner,
                             'displayname': x.displayname,
                             'description': x.description,
                             'statereason': x.state_reason,
                             'pubtoken': x.pubtoken}
            if x.pubtoken:
                sanitized_obj['pubtoken'] = base64.b64decode(x.pubtoken).rstrip('\n')
            return flask.jsonify(sanitized_obj)
    return flask.jsonify(result), 404
