===============
LSST EFD Client
===============


.. image:: https://img.shields.io/pypi/v/lsst-efd-client.svg
           :target: https://pypi.python.org/pypi/lsst-efd-client

.. image:: https://img.shields.io/travis/lsst-sqre/lsst-efd-client.svg
           :target: https://travis-ci.org/lsst-sqre/lsst-efd-client



Utility classes for working with the LSST EFD.


* Free software: MIT license


Features
--------

* The client `EfdClient`, has several useful functions.

  * `get_topics`: Return the topics in the EFD.
  * `get_fields`: Return the fields in a particular topic
  * `build_time_range_query`: Build an InfluxQL query for a topic and time range
  * `select_time_series`: Return a DataFrame containing results of a time range query
  * `select_packed_time_series`: Return a DataFrame with high cadence telemetry expanded into a single DataFrame.
  * `select_top_n`: Return a DataFrame with the results of just the most recent rows.

See example notebooks here_.

.. _here: https://github.com/lsst-sqre/notebook-demo/tree/master/experiments/efd

Authentication
--------------

Credentials for authenticating to available EFDs are held in a special file on disk.
By default, this location is `~/.lsst/notebook_auth.yaml`.
The file must exist and must have `006` permissions set.
The format of the file is a YAML dictionary of valid EFD names.
Each EFD entry should contain the username, password, and host for the EFD.
Currently, my file looks like this:

.. code-block:: yaml

  lab_efd:
    username: <user>
    password: <passwd>
    host: "test-influxdb-efd.lsst.codes"
  summit_efd:
    username: <user>
    password: <passwd>
    host: "influxdb-summit-efd.lsst.codes"

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
