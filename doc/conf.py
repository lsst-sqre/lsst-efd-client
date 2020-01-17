"""Sphinx configuration file.

This configuration only affects single-package Sphinx documentation builds.
"""

from documenteer.sphinxconfig.stackconf import build_package_configs
import lsst_efd_client


_g = globals()
_g.update(build_package_configs(
    project_name='lsst-efd-client',
    version=lsst_efd_client.version.__version__))
