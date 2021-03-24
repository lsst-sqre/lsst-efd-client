===============
LSST EFD Client
===============


.. image:: https://img.shields.io/pypi/v/lsst-efd-client.svg
           :target: https://pypi.python.org/pypi/lsst-efd-client

.. image:: https://img.shields.io/travis/lsst-sqre/lsst-efd-client.svg
           :target: https://travis-ci.com/lsst-sqre/lsst-efd-client



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
  * `get_schema`: Get metadata for the fields in a particular topic.

* There are also some utilities for dealing with results of queries

  * `merge_packed_time_series`: Takes a dataframe with records that have multiple samples per entry and returns a dataframe with one record per sample.
  * `rendezvous_dataframes`: Extend on dataframe with data from another dataframe using the closest record in time in the past, in the future, or nearest overall.

See example notebooks here_.

.. _here: https://github.com/lsst-sqre/notebook-demo/tree/master/experiments/efd

For more information, see the online docs_.

.. _docs: https://efd-client.lsst.io

CONTRIBUTING
------------

For information on contributing to this project see this_ page.

.. _this: https://github.com/lsst-sqre/lsst-efd-client/blob/master/CONTRIBUTING.rst

Credits
-------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
