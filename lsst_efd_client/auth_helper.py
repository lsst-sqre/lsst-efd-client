"""Authentication helpers
"""

import requests
from urllib.parse import urljoin


class NotebookAuth:
    """Class to help keep authentication credentials secret.

    Credentials can be retrieved either from a service endopint or
    from a file on disk.  The credential location is checked in that order.

    Parameters
    ----------
    service_endpoint : `str`, optional
        Endopint of the service to use for credentials.
        (https://roundtable.lsst.codes/segwarides/ by default)

    Raises
    ------
    RuntimeError
        Raised if teh service returns a non-200 status code.
    """

    def __init__(self, service_endpoint="https://roundtable.lsst.codes/segwarides/"):
        response = requests.get(service_endpoint)
        if response.status_code == 200:
            self.service_endpoint = service_endpoint
        else:
            raise RuntimeError(f"Credential service at {service_endpoint} failed with Error "
                               f"{response.status_code}.")

    def get_auth(self, alias, version=2):
        if version !=1 and version !=2:
            raise RuntimeError(f"Authentication version must be 1 or 2")
        if version == 1:
            return self.get_auth_v1(alias)
        return self.get_auth_v2(alias)
        
    def get_auth_v1(self, alias):
        """Return the InfluxDB v1 credentials as a tuple

        Parameters
        ----------
        alias : `str`
            Name of the authenticator.

        Returns
        -------
        credentials : `tuple`
            A tuple containing the host name, schema registry, port,
            username, password and path.
        """
        response = requests.get(urljoin(self.service_endpoint, f"creds/{alias}"))
        if response.status_code == 200:
            data = response.json()
            return (data['host'], data['schema_registry'], data['port'],
                    data['username'], data['password'], data['path'])
        elif response.status_code == 404:
            raise ValueError(f"No credentials available for {alias}. "
                             "Try list_auth to get a list of available keys.")
        else:
            raise RuntimeError(f"Server returned {response.status_code}.")

    def get_auth_v2(self, alias):
        """Return the InfluxDB v1 credentials as a tuple

        Parameters
        ----------
        alias : `str`
            Name of the authenticator.

        Returns
        -------
        credentials : `tuple`
            A tuple containing the host name, schema registry, port,
            organization, bucket, token, and path.
        """
        response = requests.get(urljoin(self.service_endpoint, f"creds/{alias}"))
        if response.status_code == 200:
            data = response.json()
            return (data['host'], data['schema_registry'], data['port'],
                    data['organization'], data['bucket'], data['token'],
                    data['path'])
        elif response.status_code == 404:
            raise ValueError(f"No credentials available for {alias}. "
                             "Try list_auth to get a list of available keys.")
        else:
            raise RuntimeError(f"Server returned {response.status_code}.")
        
    def list_auth(self):
        """Return a list of possible credential aliases
        Returns
        -------
        aliases : `list`
            A tuple of `str` that indicate valid aliases to use to retrieve
            credentials.
        """
        response = requests.get(urljoin(self.service_endpoint, "list"))
        return response.json()
