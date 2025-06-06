"""Handy helper functions for model evaluations."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../src/inference/evaluation_helper.ipynb.

# %% auto 0
__all__ = ['get_srvs', 'get_unitaries']

# %% ../../src/inference/evaluation_helper.ipynb 2
from ..imports import *
from ..utils.async_fn import run_parallel_jobs
from ..platform.simulation import Simulator 

# %% ../../src/inference/evaluation_helper.ipynb 4
def get_srvs(simulator: Simulator, backend_obj_list: Sequence, n_jobs: int = 1, **kwargs): 
    """Returns SRVs of a given list of backen objects `backend_obj_list`."""
    def _f(backend_obj):
        return simulator.backend.schmidt_rank_vector(backend_obj, **kwargs)
        
    return run_parallel_jobs(_f, backend_obj_list, n_jobs)

# %% ../../src/inference/evaluation_helper.ipynb 6
def get_unitaries(simulator: Simulator, backend_obj_list: Sequence, n_jobs: int = 1, **kwargs):
    """Returns unitaries of a given list of backen objects `backend_obj_list`."""
    def _f(backend_obj):
        return simulator.backend.get_unitary(backend_obj, **kwargs)
        
    return run_parallel_jobs(_f, backend_obj_list, n_jobs)
