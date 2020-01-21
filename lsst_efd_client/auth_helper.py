"""Authentication helpers
"""

import os
import stat
import yaml


class NotebookAuth:
    """Class to help keep authentication credentials secret.

    Credentials can be passed directly in a dictionary, the name of an
    environment variable that contains the path to the credentials file may be
    passed, or a path to the file may be passed directly.  The credential
    location is checked in that order.

    Parameters
    ----------
    path : `str`, optional
        Path to thuse when reading credentials from disk
        ('~/.lsst/notebook_auth.yaml' by default).
    env_var : `str`, optional
        Name of an environment variable to check for the
        path to the credentials file (`None` by default).
    auth_dict : `dict`, optional
        Dictionary of dictionaries of credentials.  Each key is the name of
        a potential authenticator.  The credential dictionaries must have the
        following keys: 'host', 'username', and 'password'.  This is None by
        default.

    Raises
    ------
    ValueError
       Raised if ``auth_dict``, ``env_var``, and ``path`` are all `None`.
    IOError
       Raised if either the credentials file has the wrong permissions or
       if the file fails to load.
    """

    def __init__(self, path='~/.lsst/notebook_auth.yaml', env_var=None, auth_dict=None):
        if auth_dict is not None:
            self.auth_dict = auth_dict
            return
        if env_var is not None and env_var in os.environ:
            secret_path = os.path.expanduser(os.environ[env_var])
        elif path is None:
            raise ValueError(
                "No default path provided to auth file")
        else:
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
        except Exception as exc:
            raise IOError(
                "Unable to load auth file: " +
                secret_path) from exc

    def get_auth(self, alias):
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
