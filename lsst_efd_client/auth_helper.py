import os
import stat
import yaml


class NotebookAuth:
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
        if mode & (stat.S_IRWXG | stat.S_IRWXO) != 0:
            raise IOError(
                "Auth file {secret_path} has incorrect permissions: "
                "{mode:o}".format(secret_path, mode))

        try:
            with open(secret_path) as secret_file:
                self.auth_dict = yaml.safe_load(secret_file)
        except Exception as exc:
            raise IOError(
                "Unable to load auth file: " +
                secret_path) from exc

    def get_auth(self, alias):
        return (self.auth_dict[alias]['host'], self.auth_dict[alias]['username'],
                self.auth_dict[alias]['password'])
