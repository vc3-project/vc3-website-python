
import flask
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
                             'action': vc.action}
            if vc.statusinfo is not None:
                sanitized_obj['statusinfo_error'] = vc.statusinfo[vc.cluster]['error']
                sanitized_obj['statusinfo_idle'] = vc.statusinfo[vc.cluster]['idle']
                sanitized_obj['statusinfo_node_number'] = vc.statusinfo[vc.cluster]['node_number']
                sanitized_obj['statusinfo_requested'] = vc.statusinfo[vc.cluster]['requested']
                sanitized_obj['statusinfo_running'] = vc.statusinfo[vc.cluster]['running']

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
                             'owner': x.owner,
                             'displayname': x.displayname,
                             'description': x.description}
            return flask.jsonify(sanitized_obj)
    return flask.jsonify(result), 404
