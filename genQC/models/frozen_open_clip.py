# AUTOGENERATED! DO NOT EDIT! File to edit: ../../src/models/frozen_open_clip.ipynb.

# %% auto 0
__all__ = ['FrozenOpenCLIPEmbedder_config', 'FrozenOpenCLIPEmbedder', 'CachedFrozenOpenCLIPEmbedder']

# %% ../../src/models/frozen_open_clip.ipynb 2
from ..imports import *
from .config_model import Config_Model
import open_clip

# %% ../../src/models/frozen_open_clip.ipynb 4
@dataclass
class FrozenOpenCLIPEmbedder_config:
    arch: str
    version: str
    device: str
    max_length: int
    freeze: bool
    layer: str

# %% ../../src/models/frozen_open_clip.ipynb 5
class FrozenOpenCLIPEmbedder(Config_Model):
    """Loads and freezes the [OpenCLIP](https://github.com/mlfoundations/open_clip) transformer encoder for text prompts."""
    
    LAYERS = [
        # "pooled",
        "last",
        "penultimate"
    ]

    def __init__(self, arch="ViT-H-14", version="laion2b_s32b_b79k", device="cpu", max_length=77, freeze=True, layer="penultimate"):
        super().__init__()               
        assert layer in self.LAYERS     
        self.params_config = FrozenOpenCLIPEmbedder_config(arch, version, device, max_length, freeze, layer)
        
        model, _, _ = open_clip.create_model_and_transforms(arch, device=torch.device(device), pretrained=version)
        del model.visual
        
        self.model = model
        self.to(device)
               
        assert max_length <= 77   # max set by the clip 
        self.max_length = max_length
        
        if freeze: self.freeze()
        
        self.layer = layer
        if   self.layer == "last":         self.layer_idx = 0
        elif self.layer == "penultimate":  self.layer_idx = 1
        else: raise NotImplementedError()

        #create empty token, can also be, e.g., A nice picture
        self.empty_token = self.tokenize_and_push_to_device("")
        
    def freeze(self):
        self.model = self.model.eval()
        
        for param in self.parameters(): 
            param.requires_grad = False    
            
        for param in self.model.parameters(): 
            param.requires_grad = False
    
    def to(self, device):
        self.model  = self.model.to(device)           
        self.device = device
        return self
        
    @torch.no_grad()
    def tokenize_and_push_to_device(self, text, to_device=True):
        tokens = open_clip.tokenize(text)
        if to_device:
            tokens = tokens.to(self.device)
        return tokens
    
    @torch.no_grad()
    def forward(self, c, **kwargs):
        return self.encode_with_transformer(c)

    @torch.no_grad()
    def encode_with_transformer(self, text):
        x = self.model.token_embedding(text)  # [batch_size, n_ctx, d_model]
        x = x + self.model.positional_embedding[None, :x.shape[1]]
        x = x.permute(1, 0, 2)  # NLD -> LND
        x = self.text_transformer_forward(x, attn_mask=self.model.attn_mask)
        x = x.permute(1, 0, 2)  # LND -> NLD
        x = self.model.ln_final(x)
        return x

    @torch.no_grad()
    def text_transformer_forward(self, x: torch.Tensor, attn_mask=None):
        for i, r in enumerate(self.model.transformer.resblocks):
            if i == len(self.model.transformer.resblocks) - self.layer_idx:
                break
            #if self.model.transformer.grad_checkpointing and not torch.jit.is_scripting():
                #x = checkpoint(r, x, attn_mask)
            #else:
            
            x = r(x, attn_mask=attn_mask)
            
        return x

    #--------------------------------------------------------------
    
    def get_config(self, save_path=None, without_metadata=False):
        return super().get_config(save_path=None, without_metadata=without_metadata)
    
    def store_model(self, config_path: str, save_path: str=None, without_metadata=False):        
        super().store_model(config_path, save_path=None, without_metadata=without_metadata)

    @staticmethod
    def from_config(config, device: torch.device, save_path: str=None):  
        config["save_path"] = None
        return Config_Model.from_config(config, device, save_path=None)        

# %% ../../src/models/frozen_open_clip.ipynb 13
class CachedFrozenOpenCLIPEmbedder(FrozenOpenCLIPEmbedder):
    """Adds caching support to `FrozenOpenCLIPEmbedder`."""
    
    @torch.no_grad()
    def generate_cache(self, str_list: list=None, tokens=None, cached_empty_token_index=0, b_size=2048, y_on_cpu=False):       
        self.cached_empty_token_index = cached_empty_token_index       
        if exists(str_list): self.cached_tokens = self.tokenize_and_push_to_device(str_list)      
        elif exists(tokens): self.cached_tokens = tokens
        else: raise RuntimeError("please provide str_list or tokens")
        
        # note: we need to split the tokens in batches for forward pass, n gets large
        # cached_tokens     [n, 77]      ... int
        # cached_embeddings [n, 77, 512] ... float

        n = self.cached_tokens.shape[0]
        
        n_chunks = int(np.ceil(n / b_size))
        
        in_device = self.cached_tokens.device
                
        last_ind = 0
        for i, cached_tokens in tqdm(enumerate(self.cached_tokens.chunk(n_chunks)), total=n_chunks):
            
            x = super().forward(cached_tokens.to(self.device))
            
            if i == 0:
                mem = n * x.shape[1] * x.shape[2] * x.element_size() * 1e-9
                print(f"[INFO]: caching trying to allocate memory {(n, x.shape[1], x.shape[2])} on {'cpu' if y_on_cpu else self.device} approx. {mem:.3f} GB")
                self.cached_embeddings = torch.zeros((n, x.shape[1], x.shape[2]), device="cpu" if y_on_cpu else self.device, dtype=x.dtype) # alloc huge memory !!
                
            self.cached_embeddings[last_ind:last_ind+x.shape[0]] = x.to(self.cached_embeddings.device)
            
            last_ind += x.shape[0]
            
        if not y_on_cpu:
            self.cached_embeddings = self.cached_embeddings.to(in_device)

    @torch.no_grad()
    def look_up_cos_sim_cached_index(self, str_list: list=None, tokens=None):
        if exists(str_list): tokens = self.tokenize_and_push_to_device(str_list)      
        else: raise RuntimeError("please provide str_list or tokens")
                                         
        emb   = super().forward(tokens.to(self.device))
        c_emb = self.cached_embeddings
        #-----------------
        # do cos sim search
        
        emb   = emb.flatten(start_dim=1)   # [m, seq*ch]
        c_emb = c_emb.flatten(start_dim=1) # [n, seq*ch]

        norm_emb   =   emb / torch.linalg.vector_norm(  emb, dim=1, keepdim=True)
        norm_c_emb = c_emb / torch.linalg.vector_norm(c_emb, dim=1, keepdim=True) 
 
        sim     = torch.matmul(norm_c_emb, norm_emb.T) # matmul out is [n, m]
        max_idx = torch.argmax(sim, dim=0)             # reduce the c_emb dim, [m]
     
        return max_idx       
                            
    @torch.no_grad()
    def forward(self, c, **kwargs):  
        in_device = c.device
        
        if   c.dim() == 1: return self.cached_embeddings[c.to(self.cached_embeddings.device)].to(in_device)         #list of ints       
        elif c.dim() == 2: return super().forward(c, **kwargs)   #tokenized input      
        else: raise NotImplementedError("")
