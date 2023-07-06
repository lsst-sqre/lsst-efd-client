# LSST EFD Client

![PyPI](https://img.shields.io/pypi/v/lsst-efd-client)

The LSST EFD Client helps you access the LSST Engineering Facility Database (EFD) inside [Sasquatch](https://sasquatch.lsst.io), which is backed by InfluxDB.
The client, `EfdClient`, handles authentication and provides convenience methods for accessing data in ready-to-use formats:

## Features

- The client `EfdClient`, has several useful functions.

  - `get_topics`: Return the topics in the EFD.
  - `get_fields`: Return the fields in a particular topic
  - `build_time_range_query`: Build an InfluxQL query for a topic and time range
  - `select_time_series`: Return a DataFrame containing results of a time range query
  - `select_packed_time_series`: Return a DataFrame with high cadence telemetry expanded into a single DataFrame.
  - `select_top_n`: Return a DataFrame with the results of just the most recent rows.
  - `get_schema`: Get metadata for the fields in a particular topic.

- There are also some utilities for dealing with results of queries

  - `merge_packed_time_series`: Takes a dataframe with records that have multiple samples per entry and returns a dataframe with one record per sample.
  - `rendezvous_dataframes`: Extend on dataframe with data from another dataframe using the closest record in time in the past, in the future, or nearest overall.

Example notebooks are available in [lsst-sqre/system-test](https://github.com/lsst-sqre/system-test/tree/main/efd_examples).

Documentation is available at https://efd-client.lsst.io.

## About

The LSST EFD Client was created by Simon Krughoff and continues to be maintained by his friends and colleagues on the SQuaRE team.
