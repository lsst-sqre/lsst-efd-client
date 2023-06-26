"""
Collection of EFD utilities
"""
__version__ = "__version__ = '0.12.0'"
from .auth_helper import NotebookAuth
from .efd_helper import EfdClient
from .efd_utils import (merge_packed_time_series, rendezvous_dataframes,
                        resample)

__all__ = [
    "NotebookAuth",
    "EfdClient",
    "resample",
    "rendezvous_dataframes",
    "merge_packed_time_series",
]
