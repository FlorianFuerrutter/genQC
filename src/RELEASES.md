
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