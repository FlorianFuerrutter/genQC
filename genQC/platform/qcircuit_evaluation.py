# AUTOGENERATED! DO NOT EDIT! File to edit: ../../src/platform/qcircuit_evaluation.ipynb.

# %% auto 0
__all__ = ['sort_into_bins', 'extract_gate_number', 'get_gate_stat_from_tensors', 'get_gate_stat_from_circuits']

# %% ../../src/platform/qcircuit_evaluation.ipynb 2
from ..imports import *
from .qcircuit_dataset_construction import *
from .simulation.qcircuit_sim import schmidt_rank_vector, optimize_circuit

import qiskit.quantum_info as qi
from qiskit import QuantumCircuit

# %% ../../src/platform/qcircuit_evaluation.ipynb 4
def sort_into_bins(x, y, y_uniques):
    
    x_binned = []
    y_binned = []
    
    for y_unique in y_uniques:
    
        comp    = torch.all(y==y_unique, dim=-1)
        indices = comp.nonzero().squeeze()
        
        x_binned.append(x[indices])
        y_binned.append(y[indices])
    
    y_bins = [y[0] for y in y_binned]
    
    return x_binned, y_binned, y_bins

# %% ../../src/platform/qcircuit_evaluation.ipynb 5
def extract_gate_number(qc: QuantumCircuit, gate_pool, max_gates):    
    gate_classes = {"empty":0} | {x().name:i+1 for i,x in enumerate(gate_pool)}
       
    gate_cnt = np.zeros(len(gate_classes), dtype=int)   
    
    if hasattr(qc, "data"):    
        for t, gate in enumerate(qc.data):   
            gate_id = gate_classes[gate.operation.name]       
            gate_cnt[gate_id] += 1
                
    gate_cnt[0] = max_gates - sum(gate_cnt[1:])
        
    return gate_cnt, gate_classes

# %% ../../src/platform/qcircuit_evaluation.ipynb 6
def get_gate_stat_from_tensors(tensors, gate_pool):
    for i,tensor in tqdm(enumerate(tensors), total=tensors.shape[0]):       
        qc = decode_circuit(tensor, gate_pool)
        
        t_gate_cnts, gate_dict = extract_gate_number(qc, gate_pool, max_gates=tensor.shape[1])
  
        if i > 0: gate_cnts = np.vstack([gate_cnts, t_gate_cnts])
        else:     gate_cnts = t_gate_cnts

    return gate_cnts, gate_dict

# %% ../../src/platform/qcircuit_evaluation.ipynb 7
def get_gate_stat_from_circuits(qcs: list, gate_pool, max_gates):
    for i,qc in tqdm(enumerate(qcs), total=len(qcs)):
        
        t_gate_cnts, gate_dict = extract_gate_number(qc, gate_pool, max_gates)
  
        if i > 0: gate_cnts = np.vstack([gate_cnts, t_gate_cnts])
        else:     gate_cnts = t_gate_cnts

    return gate_cnts, gate_dict
