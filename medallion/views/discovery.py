from flask import Blueprint, Response, current_app, json

from . import MEDIA_TYPE_TAXII_V21
from .. import auth
from ..exceptions import ProcessingError

mod = Blueprint("discovery", __name__)


@mod.route("/taxii2/", methods=["GET"])
@auth.login_required
def get_server_discovery():
    """
    Defines TAXII API - Server Information:
    Server Discovery section (4.1) <link here>`__

    Returns:
        discovery: A Discovery Resource upon successful requests. Additional information here <link here>`__.

    """
    # Having access to the discovery method is only related to having
    # credentials on the server. The metadata returned might be different
    # depending upon the credentials.
    server_discovery = current_app.medallion_backend.server_discovery()

    if server_discovery:
        return Response(
            response=json.dumps(server_discovery),
            status=200,
            mimetype=MEDIA_TYPE_TAXII_V21,
        )
    raise ProcessingError("Server discovery information not available", 404)


@mod.route("/<string:api_root>/", methods=["GET"])
@auth.login_required
def get_api_root_information(api_root):
    """
    Defines TAXII API - Server Information:
    Get API Root Information section (4.2) <link here>`__

    Args:
        api_root (str): the base URL of the API Root

    Returns:
        api-root: An API Root Resource upon successful requests. Additional information here <link here>`__.

    """
    # TODO: Check if user has access to objects in collection.
    root_info = current_app.medallion_backend.get_api_root_information(api_root)

    if root_info:
        return Response(
            response=json.dumps(root_info),
            status=200,
            mimetype=MEDIA_TYPE_TAXII_V21,
        )
    raise ProcessingError("API root '{}' information not found".format(api_root), 404)


@mod.route("/<string:api_root>/status/<string:status_id>/", methods=["GET"])
@auth.login_required
def get_status(api_root, status_id):
    """
    Defines TAXII API - Server Information:
    Get Status section (4.3) <link here>`__

    Args:
        api_root (str): the base URL of the API Root
        status_id (str): the `identifier` of the Status message being requested

    Returns:
        status: A Status Resource upon successful requests. Additional information here <link here>`__.

    """
    # TODO: Check if user has access to the Status resource.
    status = current_app.medallion_backend.get_status(api_root, status_id)

    if status:
        return Response(
            response=json.dumps(status),
            status=200,
            mimetype=MEDIA_TYPE_TAXII_V21,
        )
    raise ProcessingError("Status '{}' not found".format(status_id), 404)
