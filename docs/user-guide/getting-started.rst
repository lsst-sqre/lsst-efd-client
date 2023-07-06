###############
Getting started
###############

Installation
============

The LSST EFD Client is preinstalled in the ``rubin-env-rsp`` and ``rubin-env-developer`` Conda-Forge metapackages, which is the default Python environment for the `Rubin Science Platform`_.
You can check if ``lsst_efd_client`` is available at a Python prompt:

.. prompt:: python >>>

   import lsst_efd_client

If not available, you can install with either Conda or pip:

.. tab-set::

   .. tab-item:: pip

      .. prompt:: bash

         pip install lsst-efd-client

   .. tab-item:: Conda

      .. prompt:: bash

         conda install -c conda-forge lsst-efd-client

Next steps
==========

- See the example EFD notebooks in the `lsst-sqre/system-test repository`_.
- Refer to the :ref:`py-api`.
