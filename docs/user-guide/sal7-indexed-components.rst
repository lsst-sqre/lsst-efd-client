#############################################################
Retrieving indexed component information in SAL 6 and earlier
#############################################################

When SAL 7 is released, the field name for indexed components will change to ``salIndex`` from ``{CSCName}ID``.
The queries in the EFD client have been adjusted to use the new name when passing the *index* parameter.

A boolean argument, ``use_old_csc_indexing``, is available on all queries methods in `~lsst_efd_client.EfdClient` that allows your to retrieve the old field name.
Set this flag to `True` in order to get the old indexing scheme.

The TTS conversion to SAL 7 occurred June 27, 2022.
However, the TTS EFD operates on a 30 day rotation, so the older indexing will phase out approximately 30 days after the upgrade happens.
The summit, and by fiat the LDF replica, will convert to SAL 7 on July 6, 2022. 
Since neither database operates with a retention policy, two separate queries must be constructed in order to get data selected on an index spanning the above date.
