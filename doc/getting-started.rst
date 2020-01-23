###############
Getting started
###############

Installation
============

First, ensure that the LSST EFD Client is installed in your environment.
You can check this at a Python prompt:

.. prompt:: python >>>

   import lsst_efd_client

To install or upgrade the LSST EFD Client, use :command:`pip`:

.. prompt:: bash

   pip install -U lsst-efd-client

Authentication configuration
============================

Credentials for authenticating to available EFDs are held in a special file on disk.
By default, this location for this file is :file:`~/.lsst/notebook_auth.yaml`.
The file must exist and must have ``006`` permissions set.
To set the correct permissions execute the following command in a shell:

.. code:: bash

  chmod 600 ~/.lsst/notebook_auth.yaml

The format of the file is a YAML dictionary of valid EFD names.
Each EFD entry should contain the username, password, and host for the EFD.
This is an example of an auth file for "Lab" and "Summit" EFDs:

.. code-block:: yaml

  lab_efd:
    username: <user>
    password: <passwd>
    host: "test-influxdb-efd.lsst.codes"
  summit_efd:
    username: <user>
    password: <passwd>
    host: "influxdb-summit-efd.lsst.codes"

Next steps
==========

- See the example EFD notebooks in the `lsst-sqre/notebook-demo repository <https://github.com/lsst-sqre/notebook-demo/tree/master/experiments/efd>`_.
- Refer to the :ref:`py-api`.
