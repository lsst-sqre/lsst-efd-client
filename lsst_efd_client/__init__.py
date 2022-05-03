"""
Collection of EFD utilities
"""
__version__ = "__version__ = '0.10.2'"
from .auth_helper import NotebookAuth
from .efd_helper import EfdClient
from .efd_utils import resample, rendezvous_dataframes, merge_packed_time_series

__all__ = ['NotebookAuth', 'EfdClient', 'resample', 'rendezvous_dataframes',
           'merge_packed_time_series']
