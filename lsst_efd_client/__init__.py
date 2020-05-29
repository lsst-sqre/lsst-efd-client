"""
Collection of EFD utilities
"""
__version__ = "__version__ = '0.5.0'"
from .auth_helper import NotebookAuth
from .efd_helper import EfdClient
from .efd_utils import resample

__all__ = ['NotebookAuth', 'EfdClient', 'resample']
