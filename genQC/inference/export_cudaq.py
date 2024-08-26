# AUTOGENERATED! DO NOT EDIT! File to edit: ../../src/inference/export_cudaq.ipynb.

# %% auto 0
__all__ = ['backend', 'CircuitInstruction', 'CircuitInstructions', 'CircuitsCudaqBackend', 'tensor_to_instructions',
           'genqc_to_cudaq']

# %% ../../src/inference/export_cudaq.ipynb 2
from ..imports import *
from typing import Sequence, List, Optional
import cudaq

# %% ../../src/inference/export_cudaq.ipynb 4
@dataclass
class CircuitInstruction():
    name: str
    control_nodes: Sequence[int]
    target_nodes: Sequence[int]
    params: Sequence[float]

# %% ../../src/inference/export_cudaq.ipynb 5
class CircuitInstructions():
    def __init__(self, tensor_shape: torch.Size) -> None:
        assert len(tensor_shape) == 2   # ... [qubits, time]
        self.tensor_shape  = tensor_shape     
        self._instructions = []
        self.instruction_names_set = set()
    
    def add_instruction(self,  
                        name: str, 
                        control_nodes: Sequence[int], 
                        target_nodes: Sequence[int], 
                        params: Sequence[float]) -> None:
        self.instruction_names_set.add(name)
        self._instructions.append(CircuitInstruction(name, control_nodes, target_nodes, params))

    @property
    def data(self) -> List[CircuitInstruction]: return self._instructions

    @property
    def length(self) -> int: return len(self._instructions)

    @property
    def num_qubits(self) -> int: return self.tensor_shape[0]

    @property
    def max_gates(self) -> int: return self.tensor_shape[1]
    
    def __repr__(self) -> str: return str(self._instructions)

    def print(self) -> None:
        for instruction in self.data: 
            print(instruction)        

# %% ../../src/inference/export_cudaq.ipynb 7
class CircuitsCudaqBackend():

    BASIC_BACKEND_TYPE = type[cudaq.kernel]
    
    # Has to match with insides of belows kernel
    KERNEL_VOCABULARY = {"h":1, "cx":2, "z":3, "x":4, "y":5, "ccx":6, "swap":7} 
    
    def _construct_kernel(self,
                          gate_list: List[str],
                          target_1_nodes_list: List[int],
                          target_2_nodes_list: List[int],
                          control_1_nodes_list: List[int],
                          control_2_nodes_list: List[int]
                         ) -> cudaq.kernel:
        """Construct a `cudaq.kernel` from provided paramters."""
  
        num_gates = len(gate_list)
        gate_list = [self.KERNEL_VOCABULARY[g] for g in gate_list]

        # Note: `@cudaq.kernel` decorator has a overhead of 20ms, regardless of the for-loop inside
        
        @cudaq.kernel
        def place_gate_kernel(gate: int, 
                              qvector: cudaq.qview,
                              target_1: int, 
                              target_2: int, 
                              control_1: int, 
                              control_2: int):        
            if   gate == 1: h(qvector[target_1])
            elif gate == 2: cx(qvector[control_1], qvector[target_1])
            elif gate == 3: z(qvector[target_1])
            elif gate == 4: x(qvector[target_1])
            elif gate == 5: y(qvector[target_1])
            elif gate == 6: x.ctrl(qvector[control_1], qvector[control_2], qvector[target_1])
            elif gate == 7: swap(qvector[target_1], qvector[target_2])
      
        @cudaq.kernel  
        def kernel(input_state: List[complex]):
            qvector = cudaq.qvector(input_state)
            for i in range(num_gates):
                place_gate_kernel(gate_list[i], qvector, target_1_nodes_list[i], target_2_nodes_list[i], control_1_nodes_list[i], control_2_nodes_list[i])
    
        return kernel

    def check_error_circuit(self, 
                            gate: str, 
                            num_target_nodes: int, 
                            num_control_nodes: int) -> bool:
        """Check number of connections of given gate. Used to check for error circuits."""

        if gate not in self.KERNEL_VOCABULARY:
            raise NotImplementedError(f"Unknown gate {gate}, not in `self.KERNEL_VOCABULARY`.")
            
        if gate in ["h", "z", "x", "y"]:
            if num_target_nodes != 1 or num_control_nodes !=0: return False

        elif gate in ["cx"]:
            if num_target_nodes != 1 or num_control_nodes !=1: return False

        elif gate in ["ccx"]:
            if num_target_nodes != 1 or num_control_nodes !=2: return False

        elif gate in ["swap"]:
            if num_target_nodes != 2 or num_control_nodes !=0: return False

        else:
            raise NotImplementedError(f"Unknown gate {gate}, implemetation is faulty!")

        return True

    
    def export_cudaq(self, instructions: CircuitInstructions) -> cudaq.kernel:
        """Convert given genQC `CircuitInstructions` to a `cudaq.kernel`."""

        # num_qubits = instructions.num_qubits
        num_gates  = instructions.length

        # @cudaq.kernel can only take list[int] and no str directly
        # -> we have to map everything to list[int]        
        # set default value to 9999 so an error wil be raised if we have a faulty tensor encoding
        
        gate_list = []
        target_1_nodes_list  = [9999] * num_gates
        target_2_nodes_list  = [9999] * num_gates
        control_1_nodes_list = [9999] * num_gates
        control_2_nodes_list = [9999] * num_gates

        for i, instruction in enumerate(instructions.data):

            gate          = instruction.name.lower()
            control_nodes = instruction.control_nodes
            target_nodes  = instruction.target_nodes
 
            if len(instruction.params) > 0:
                raise NotImplementedError(f"Only support non parametrized gates currently.")
            
            num_target_nodes  = len(target_nodes)
            num_control_nodes = len(control_nodes)
            
            if not self.check_error_circuit(gate, num_target_nodes, num_control_nodes):
                return None
            
            gate_list.append(gate)
  
            if num_target_nodes > 0:
                target_1_nodes_list[i] = target_nodes[0]
                if num_target_nodes > 1: 
                    target_2_nodes_list[i] = target_nodes[1]      
            
            if num_control_nodes > 0:
                control_1_nodes_list[i] = control_nodes[0]  
                if num_control_nodes > 1: 
                    control_2_nodes_list[i] = control_nodes[1]  
                    
        #--------------------
        kernel= self._construct_kernel(gate_list, target_1_nodes_list, target_2_nodes_list, control_1_nodes_list, control_2_nodes_list)
        return kernel
    
    def get_unitary(self, kernel: cudaq.kernel, num_qubits: int) -> np.ndarray:
        """Return the unitary matrix of a `cudaq.kernel`. Currently relies on simulation, could change in future releases of cudaq."""
        
        N = 2**num_qubits
        U = np.zeros((N, N), dtype=np.complex128)
        
        for j in range(N): 
            state_j    = np.zeros((N), dtype=np.complex128) 
            state_j[j] = 1
            
            U[:, j] = np.array(cudaq.get_state(kernel, state_j), copy=False)
            
        return U

    def draw(self, kernel: cudaq.kernel, num_qubits: int, **kwargs) -> None:
        """Draw the given `cudaq.kernel` using cudaq.""" 
        c    = [0] * (2**num_qubits)
        c[0] = 1
        print(cudaq.draw(kernel, c))

# %% ../../src/inference/export_cudaq.ipynb 9
def tensor_to_instructions(tensor: torch.Tensor, 
                           vocabulary_inverse: dict, 
                           params_tensor: Optional[torch.Tensor] = None, 
                           params_4pi_normalization: bool = True,
                           sign_labels: dict = {"control_nodes":-1, "target_nodes":+1}) -> CircuitInstructions:
    """Convert a given `torch.Tensor` to `CircuitInstructions`."""
 
    assert tensor.dim() == 2, f"{tensor.shape=}"
    num_of_qubits, time = tensor.shape
    
    instructions = CircuitInstructions(tensor_shape=tensor.shape)
    
    for t in range(time):         
        enc_time_slice = tensor[:, t] # contains all bits at time t   
    
        for gate_index, gate in vocabulary_inverse.items():   
        
            target_nodes  = (enc_time_slice == (sign_labels["target_nodes"]  * gate_index)).nonzero(as_tuple=True)[0]
            control_nodes = (enc_time_slice == (sign_labels["control_nodes"] * gate_index)).nonzero(as_tuple=True)[0]
    
            if target_nodes.nelement() > 0:                                   
                params = []
                if exists(params_tensor):
                    params = params_tensor[:, t]
                    if params_4pi_normalization:
                        params = (params+1.0) * 2.0*np.pi    # [-1, 1] to [0, 4pi]
                    params = params.tolist()

                instructions.add_instruction(gate, control_nodes.tolist(), target_nodes.tolist(), params)
                
                break  #break on first hit, per def only one gate allowed per t
          
            elif control_nodes.nelement() > 0: # no target but control means error
                raise RuntimeError("target_nodes.nelement() <= 0 but control_nodes.nelement() > 0")
                
            #else we are fine with tensors that have time steps with no action!
    
    return instructions

# %% ../../src/inference/export_cudaq.ipynb 10
backend = CircuitsCudaqBackend()

def genqc_to_cudaq(tensor: torch.Tensor, vocabulary_inverse: dict) -> cudaq.kernel:
    """Convert given `torch.Tensor` to a `cudaq.kernel`."""
    instructions = tensor_to_instructions(tensor, vocabulary_inverse) 
    kernel       = backend.export_cudaq(instructions)
    return kernel
