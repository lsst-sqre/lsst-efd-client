.. py:currentmodule:: lsst_efd_client

###################
The LSST EFD Client
###################

The LSST EFD Client helps you access the LSST Engineering Facility Database (EFD), which is backed by InfluxDB.
The client, `EfdClient` handles authentication and provides convenience methods for accessing data in ready-to-use formats:

`~EfdClient.get_topics`
    Get the topics in the EFD.
`~EfdClient.get_fields`
    Get the fields in a particular topic.
`~EfdClient.build_time_range_query`
    Build an InfluxQL_ query for a topic and time range.
`~EfdClient.select_time_series`:
    Get a `~pandas.DataFrame` containing results of a time range query.
`~EfdClient.select_packed_time_series`:
    Get a `~pandas.DataFrame` with high cadence telemetry expanded into a single `~pandas.DataFrame`.
`~EfdClient.select_top_n`
   Get a `~pandas.DataFrame` with the results of just the most recent rows.
`~EfdClient.get_schema`
   Return metadata about fields associated with a topic.
   This includes the description, units and an `astropy.units.Unit` where possible.
   If any of the metadata is missing in the topic definition, it will be `None` in the returned schema.

This package also provides some useful utility functions for dealing with data returned from the various `EfdClient` data access methods:

`resample`
   Resample a `pandas.DataFrame` onto the the sampling of a second `pandas.DataFrame`
`rendezvous_dataframes`
   Given one `pandas.DataFrame`, find all entries in another `pandas.DataFrame` that are closest (default is nearest in the past).

Follow the :doc:`getting-started` guide to start accessing EFD data.
Also, check out the `demo notebooks`_ for examples.

.. _InfluxQL: https://docs.influxdata.com/influxdb/v1.7/query_language/
.. _demo notebooks: https://github.com/lsst-sqre/notebook-demo/tree/master/efd_examples

.. _user-guide:

Using lsst_efd_client
=====================

.. toctree::
   :maxdepth: 2

   getting-started
   history

.. _py-api:

Python API reference
====================

.. automodapi:: lsst_efd_client
   :no-inheritance-diagram:

.. _dev-guide:

Contributing
============

``lsst_efd_client`` is developed at https://github.com/lsst-sqre/lsst-efd-client.
Please use GitHub issues in the project repository to report problems and contribute.
