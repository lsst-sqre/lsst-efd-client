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

Next steps
==========

- See the example EFD notebooks in the `lsst-sqre/system-test repository`_.
- Refer to the :ref:`py-api`.

Special Notes
=============

Retrieving Indexed Component Information
----------------------------------------

When SAL 7 is released, the field name for indexed components will change to *salIndex* from *{CSCName}ID*.
The queries in the EFD client have been adjusted to use the new name when passing the *index* parameter.
A boolean flag, *use_old_csc_indexing* has been added to all queries that allow one to retrieve the old field name.
Set this flag to `True` in order to get the old indexing scheme.
The TTS conversion to SAL 7 will take place on June 27, 2022.
However, the TTS EFD operates on a 30 day rotation, so the older indexing will phase out approximately 30 days after the upgrade happens.
The summit, and by fiat the LDF replica, will convert to SAL 7 on July 6, 2022.
Since neither database operates with a retention policy, two separate queries must be constructed in order to get data selected on an index spanning the above date.

.. _lsst-sqre/system-test repository: https://github.com/lsst-sqre/system-test/tree/main/efd_examples
