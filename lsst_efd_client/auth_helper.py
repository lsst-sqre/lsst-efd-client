"""Authentication helpers
"""

import os
import stat
import yaml
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
    path : `str`, optional
        Path to use when reading credentials from disk
        ('~/.lsst/notebook_auth.yaml' by default).

    Raises
    ------
    ValueError
       Raised if the auth file is absent or if ``path`` and ``service_endpoint``
       are both `None`.
    IOError
       Raised if either the credentials file has the wrong permissions or
       if the file fails to load.
    """

    def __init__(self, service_endpoint="https://roundtable.lsst.codes/segwarides/", path='~/.lsst/notebook_auth.yaml'):
        if service_endpoint is not None:
            response = requests.get(service_endpoint)
            if response.status_code == 200:
                self.get_auth = self.get_auth_by_service
                self.list_auth = self.list_auth_by_service
                self.service_endpoint = service_endpoint
            else:
                self.service_endpoint = None
        elif path is not None:
            secret_path = os.path.expanduser(path)
            if not os.path.isfile(secret_path):
                raise ValueError("No auth file at: {}".format(secret_path))
            mode = os.stat(secret_path).st_mode
            if stat.S_IMODE(mode) != 0o600:
                raise IOError(
                    f"Auth file {secret_path} has incorrect permissions: "
                    f"{oct(stat.S_IMODE(mode))}. Must be 0o600 instead.")

            try:
                with open(secret_path) as secret_file:
                    self.auth_dict = yaml.safe_load(secret_file)
                self.get_auth = self.get_auth_by_dict
                self.list_auth = self.list_auth_by_dict
            except Exception as exc:
                raise IOError(
                    "Unable to load auth file: " +
                    secret_path) from exc
        else:
            raise VlaueError("No mechanism for providing credentials provided. "
                             "Please specify either service_endpoint or path")

    def get_auth_by_dict(self, alias):
        """Return the credentials as a tuple

        Parameters
        ----------
        alias : `str`
            Name of the authenticator.

        Returns
        -------
        credentials : `tuple`
            A tuple containing the host name, user name, and password.
        """
        return (self.auth_dict[alias]['host'], self.auth_dict[alias]['username'],
                self.auth_dict[alias]['password'])

    def get_auth_by_service(self, alias):
        """Return the credentials as a tuple

        Parameters
        ----------
        alias : `str`
            Name of the authenticator.

        Returns
        -------
        credentials : `tuple`
            A tuple containing the host name, user name, and password.
        """
        response = requests.get(urljoin(self.service_endpoint, f"creds/{alias}"))
        if response.status_code == 200:
            data = response.json()
            return (data['host'], data['username'], data['password'])
        elif response.status_code == 404:
            raise ValueError(f"No credentials available for {alias}. "
                             "Try list_auth to get a list of available keys.")
        else:
            raise RuntimeError(f"Server returned {response.status_code}.")

    def list_auth_by_dict(self):
        """Return a list of possible credential aliases
        Returns
        -------
        aliases : `list`
            A tuple of `str` that indicate valid aliases to use to retrieve
            credentials.
        """
        return list(self.auth_dict.keys())

    def list_auth_by_service(self):
        """Return a list of possible credential aliases
        Returns
        -------
        aliases : `list`
            A tuple of `str` that indicate valid aliases to use to retrieve
            credentials.
        """
        response = requests.get(urljoin(self.service_endopint, "list"))
        return response.json()
