"""Different metrics used for evaluation."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../src/inference/eval_metrics.ipynb.

# %% auto 0
__all__ = ['BaseNorm', 'UnitaryFrobeniusNorm', 'UnitaryInfidelityNorm']

# %% ../../src/inference/eval_metrics.ipynb 2
from ..imports import *
from scipy.stats import unitary_group

# %% ../../src/inference/eval_metrics.ipynb 4
class BaseNorm(abc.ABC): 
    """Base class for norms."""
    
    @staticmethod
    @abc.abstractmethod
    def distance(approx_U: torch.Tensor, target_U: torch.Tensor) -> torch.Tensor: raise NotImplementedError()
    
    @staticmethod
    @abc.abstractmethod
    def name() -> str: raise NotImplementedError()

# %% ../../src/inference/eval_metrics.ipynb 6
class UnitaryFrobeniusNorm(BaseNorm):
    """
    The Frobenius-Norm for unitaries: defined in https://arxiv.org/pdf/2106.05649.pdf.
    """

    def __call__(self, approx_U: torch.Tensor, target_U: torch.Tensor) -> torch.Tensor:        
        return Unitary_FrobeniusNorm.distance(approx_U, target_U)
    
    @staticmethod
    def distance(approx_U: torch.Tensor, target_U: torch.Tensor) -> torch.Tensor:
        d = 0.5 * torch.linalg.matrix_norm((approx_U-target_U), ord="fro")**2
        return d
        
    @staticmethod
    def name() -> str: return "Frobenius-Norm"

# %% ../../src/inference/eval_metrics.ipynb 7
class UnitaryInfidelityNorm(BaseNorm):
    """
    The Infidelity-Norm for unitaries: defined in https://link.aps.org/accepted/10.1103/PhysRevA.95.042318, TABLE I: 1.
    """

    def __call__(self, approx_U: torch.Tensor, target_U: torch.Tensor) -> torch.Tensor:        
        return Unitary_infidelity.distance(approx_U, target_U)
    
    @staticmethod
    def distance(approx_U: torch.Tensor, target_U: torch.Tensor) -> torch.Tensor: 
        """Supports batched intputs, can be used as loss. Input shapes [b, n, n] or [n, n]."""
        d = torch.matmul(torch.transpose(target_U, -2, -1).conj(), approx_U) # out [b, n, n] or [n, n]
        d = torch.diagonal(d, offset=0, dim1=-2, dim2=-1).sum(-1)  # do partial (batched) trace, out [b, n] or [n]      
        d = 1.0 - (d / target_U.shape[-1]).abs().square()
        return d
        
    @staticmethod
    def name() -> str: return "Unitary-Infidelity"
