# genQC 0.1.0 - 26.08.2024

### Description:

- Upload of `genQC` to `pypi`. 
- Added [`CUDA-Q`](https://github.com/NVIDIA/cuda-quantum) kernel export. 
- Added hugginface model loading.
- Increased minimal python version to 3.10

### Tested on:

- Ubuntu 22.04.4 LTS
- nbdev==2.3.27 (for notebook development)
- python 3.10

**Libs**:

```txt 
torch==2.4.0
numpy==2.1.0
matplotlib==3.9.2
scipy==1.14.1
pandas==2.2.2
omegaconf==2.3.0
qiskit==1.2.0
tqdm==4.66.5
joblib==1.4.2
open-clip-torch==2.26.1
ipywidgets==8.1.5
pylatexenc==2.10
huggingface_hub==0.24.6
```


# Arxiv submission release - 07.12.2023

### Description:

First release of the codebase accompanying the paper [Quantum circuit synthesis with diffusion models](https://arxiv.org/abs/2311.02041).

Included are the configs and weights of the pre-trained models used in the paper, `genQC` our diffusion pipeline and example notebooks.

### Tested on:

Release is tested on the specific versions:

- Windows 10 with cuda 12.1
- nbdev==2.3.12 (for notebook development)
- python 3.11

**Libs**:

```txt 
torch==2.1.1+cu121
numpy==1.26.2
matplotlib==3.8.2
scipy==1.11.4
pandas==2.1.3
omegaconf==2.3.0
qiskit==0.45.1
tqdm==4.66.1
joblib==1.3.2
open-clip-torch==2.23.0
ipywidgets==8.0.4
pylatexenc==2.10
```