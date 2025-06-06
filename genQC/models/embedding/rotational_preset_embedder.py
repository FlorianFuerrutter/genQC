"""Class for a rotational preset embedder."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../../src/models/embedding/rotational_preset_embedder.ipynb.

# %% auto 0
__all__ = ['MultimodialEmbedder', 'MultimodialPresetEmbedderConfig', 'MultimodialPresetEmbedder',
           'RotationalMultimodialPresetEmbedder', 'RotationalMultimodialPresetEmbedderTiny']

# %% ../../../src/models/embedding/rotational_preset_embedder.ipynb 2
from ...imports import *
from ...utils.math import gram_schmidt
from .base_embedder import BaseEmbedder

# %% ../../../src/models/embedding/rotational_preset_embedder.ipynb 4
class MultimodialEmbedder(BaseEmbedder):
    
    def __init__(self, zero_sum_space: bool) -> None:
        super().__init__()

        self.zero_sum_space = zero_sum_space
        
        h_mean, h_std = torch.tensor(0.0), torch.tensor(1.0)
        w_mean, w_std = torch.tensor(0.0), torch.tensor(1.0)
        
        self.register_buffer('h_mean', h_mean)
        self.register_buffer('h_std', h_std)

        self.register_buffer('w_mean', w_mean)
        self.register_buffer('w_std', w_std)

    def set_scaling(self, h: torch.Tensor, w: torch.Tensor) -> None:
        self.h_mean, self.h_std = torch.tensor(0.0), torch.tensor(1.0)
        self.w_mean, self.w_std = torch.tensor(0.0), torch.tensor(1.0)

        return #disbled; not needed for new emb initialization
        
        x = self.embed(h, w)

        if not self.channel_last:
            x_h = x[:, :self.clr_dim]
            x_w = x[:, self.clr_dim:]
        else:
            x_h = x[..., :self.clr_dim]
            x_w = x[..., self.clr_dim:]
        
        self.h_mean, self.h_std = x_h.mean(), x_h.std()
        self.w_mean, self.w_std = x_w.mean(), x_w.std()
   
    def scale_emb(self, x_emb: torch.Tensor) -> torch.Tensor:
        # x_emb .. [b, ch, s, t]

        # mean
        if not self.zero_sum_space:
            if not self.channel_last:
                x_emb[:, :self.clr_dim] -= self.h_mean
                x_emb[:, self.clr_dim:] -= self.w_mean
            else:
                x_emb[..., :self.clr_dim] -= self.h_mean
                x_emb[..., self.clr_dim:] -= self.w_mean
        
        # variance
        if not self.channel_last:
            x_emb[:, :self.clr_dim] /= self.h_std
            x_emb[:, self.clr_dim:] /= self.w_std
        else:
            x_emb[..., :self.clr_dim] /= self.h_std
            x_emb[..., self.clr_dim:] /= self.w_std
              
        return x_emb

    def invert_scale_emb(self, x_emb: torch.Tensor) -> torch.Tensor:
        # x_emb .. [b, ch, s, t]

        # variance
        if not self.channel_last:
            x_emb[:, :self.clr_dim] *= self.h_std
            x_emb[:, self.clr_dim:] *= self.w_std
        else:
            x_emb[..., :self.clr_dim] *= self.h_std
            x_emb[..., self.clr_dim:] *= self.w_std

        # mean
        if not self.zero_sum_space:    
            if not self.channel_last:
                x_emb[:, :self.clr_dim] += self.h_mean
                x_emb[:, self.clr_dim:] += self.w_mean
            else:
                x_emb[..., :self.clr_dim] += self.h_mean
                x_emb[..., self.clr_dim:] += self.w_mean
        
        return x_emb

# %% ../../../src/models/embedding/rotational_preset_embedder.ipynb 6
@dataclass
class MultimodialPresetEmbedderConfig:  
    clr_dim: int
    num_clrs: int
    params_dim: int
    num_params_per_clr: int
    zero_sum_space: bool
    explicit_node_type_embeddings: bool
    channel_last: bool
    parametrized_tokens: Optional[list[int]] = None 
    unique_class_values: Optional[list[int]] = None

# %% ../../../src/models/embedding/rotational_preset_embedder.ipynb 7
class MultimodialPresetEmbedder(MultimodialEmbedder):
    """
    Embedder class for multimodial discrete and continuous data, e.g. parametrized gates/actions. 
    Embeddings are fixed and not trained.
    """
    
    def __init__(self, 
                 clr_dim: int, 
                 num_clrs: int, 
                 params_dim: int, 
                 num_params_per_clr: int, 
                 zero_sum_space: bool,
                 explicit_node_type_embeddings: bool = True,
                 channel_last: bool = True,
                 parametrized_tokens: Optional[list[int]] = None,
                 unique_class_values: Optional[list[int]] = None) -> None:
        """
        Note `explicit_node_type_embeddings` means we convert the `+-k` to all postive, but there are often unsused connection types. For instance, `1=H` the minus node is never used.

        To improve this and reduce the `clr_dim`, we can provide `unique_values` which are the only tokens that actually appear.
        """
        super().__init__(zero_sum_space=zero_sum_space)


        if exists(unique_class_values):
            assert isinstance(unique_class_values, list)
            self.unique_class_values_tensor = torch.tensor(unique_class_values)
            
            explicit_node_type_embeddings = False

            print(f"[INFO]: provided `unique_class_values` ({unique_class_values}), enforcing `num_clrs=len(unique_class_values)={len(unique_class_values)}`.")
            num_clrs = len(unique_class_values)
        
        self.explicit_node_type_embeddings = explicit_node_type_embeddings  
        self.channel_last = channel_last
        self.parametrized_tokens = parametrized_tokens
        self.unique_class_values = unique_class_values

        if (num_params_per_clr*num_clrs) > params_dim and num_params_per_clr > 0:
            print(f"[WARNING]: For `num_params_per_clr` larger 0, we need at least a `params_dim` (is {params_dim}) of"
                  f" `num_params_per_clr*num_clrs` (is {num_params_per_clr*num_clrs}),"
                  f" automatically setting `params_dim` to {num_params_per_clr*num_clrs} to inforce this!")
        
            params_dim = num_params_per_clr*num_clrs

        if self.zero_sum_space and ((num_params_per_clr*num_clrs) + 1) > params_dim and num_params_per_clr > 0:
            print(f"[WARNING]: `params_dim` is set to the minimum `num_params_per_clr*num_clrs`={num_params_per_clr*num_clrs},"
                  f" but for `{zero_sum_space=}` we need one more dimension, automatically setting it to"
                  f" `num_params_per_clr*num_clrs+1` {num_params_per_clr*num_clrs+1}.")
            
            params_dim = num_params_per_clr*num_clrs + 1
        
        if self.zero_sum_space:        
            if self.explicit_node_type_embeddings and ((num_clrs*2 - 2) + 1) > clr_dim:
                print(f"[WARNING]: `clr_dim` is set to {clr_dim} and `{explicit_node_type_embeddings=}`,"
                      f" but for `{zero_sum_space=}` we need one more dimension than the number of tokens `(num_clrs*2 - 2)` (is {(num_clrs*2 - 2)}),"
                      f" automatically setting it to `clr_dim=(num_clrs*2 - 2) + 1` {(num_clrs*2 - 2) + 1}.")

                # has empty and padd tokens, these only have the plus branch (so -2)!
                clr_dim = (num_clrs*2 - 2) + 1

            elif (num_clrs + 1) > clr_dim:
                print(f"[WARNING]: `clr_dim` is set to {clr_dim} and `{explicit_node_type_embeddings=}`,"
                      f" but for `{zero_sum_space=}` we need one more dimension than the number of tokens `num_clrs` (is {num_clrs}),"
                      f" automatically setting it to `clr_dim=num_clrs+1` {num_clrs+1}.")
                
                clr_dim = num_clrs + 1
            
        self.clr_dim            = clr_dim
        self.num_clrs           = num_clrs
        self.params_dim         = params_dim
        self.num_params_per_clr = num_params_per_clr
        
        self._num_discrete_embeddings = self.num_clrs
        self._num_param_embeddings    = self.num_params_per_clr * self.num_clrs
        self.embedding_dim            = self.clr_dim + self.params_dim

        if self.explicit_node_type_embeddings:
            # use distinct embeddings for +-k and not just +-v
            # has empty and padd tokens, these only have the plus branch (so -2)!
            self._num_discrete_embeddings = self.num_clrs*2 - 2
     
        self.num_embeddings = self._num_discrete_embeddings + self._num_param_embeddings
        self.emb_clr        = nn.Embedding(num_embeddings=self.num_embeddings, embedding_dim=self.embedding_dim)    
        print(f"[INFO]: Created `nn.Embedding` with a total of {self.num_embeddings} vectors in a {self.embedding_dim} dimensional space.")
        
        self.params_config = MultimodialPresetEmbedderConfig(clr_dim=self.clr_dim, 
                                                             num_clrs=self.num_clrs, 
                                                             params_dim=self.params_dim, 
                                                             num_params_per_clr=self.num_params_per_clr,
                                                             zero_sum_space=self.zero_sum_space,
                                                             explicit_node_type_embeddings=self.explicit_node_type_embeddings,
                                                             channel_last=self.channel_last,
                                                             parametrized_tokens=self.parametrized_tokens)
        
        self._init_weights(zero_sum_space=self.zero_sum_space)
    
    def _init_weights(self, zero_sum_space) -> None:
        self.emb_clr.weight.requires_grad = False
        
        _dtype = self.emb_clr.weight.dtype
        self.emb_clr = self.emb_clr.to(torch.float64)
        
        # keep spaces ortho with clr
        self.emb_clr.weight.data.zero_()
        nn.init.orthogonal_(self.emb_clr.weight.data[:self._num_discrete_embeddings, :self.clr_dim])
        nn.init.orthogonal_(self.emb_clr.weight.data[self._num_discrete_embeddings:, self.clr_dim:])

        if zero_sum_space:
            assert self._num_discrete_embeddings < self.clr_dim, f"{self._num_discrete_embeddings} < {self.clr_dim}"
            if self._num_param_embeddings > 0:
                assert self._num_param_embeddings < self.params_dim, f"{self._num_param_embeddings} < {self.params_dim}"
 
            # Convert to zero-sum space
            self.emb_clr.weight.data[:self._num_discrete_embeddings, :self.clr_dim] -= torch.mean(self.emb_clr.weight.data[:self._num_discrete_embeddings, :self.clr_dim], dim=-1, keepdim=True) 
            if self._num_param_embeddings > 0:
                self.emb_clr.weight.data[self._num_discrete_embeddings:, self.clr_dim:] -= torch.mean(self.emb_clr.weight.data[self._num_discrete_embeddings:, self.clr_dim:], dim=-1, keepdim=True) 

            # Orthonormalization that conserves zero-sum space
            self.emb_clr.weight.data[:self._num_discrete_embeddings, :self.clr_dim] = gram_schmidt(self.emb_clr.weight.data[:self._num_discrete_embeddings, :self.clr_dim])
            if self._num_param_embeddings > 0:
                self.emb_clr.weight.data[self._num_discrete_embeddings:, self.clr_dim:] = gram_schmidt(self.emb_clr.weight.data[self._num_discrete_embeddings:, self.clr_dim:])
            
        self.emb_clr.weight.data[:self._num_discrete_embeddings, :self.clr_dim] /= torch.std(self.emb_clr.weight.data[:self._num_discrete_embeddings, :self.clr_dim], dim=-1, keepdim=True, correction=0)
        if self._num_param_embeddings > 0:
            self.emb_clr.weight.data[self._num_discrete_embeddings:, self.clr_dim:] /= torch.std(self.emb_clr.weight.data[self._num_discrete_embeddings:, self.clr_dim:], dim=-1, keepdim=True, correction=0)   
        
        self.emb_clr = self.emb_clr.to(_dtype)
        
    def print_emb_matrix(self) -> None:
        print(self.emb_clr.weight.data)

    #-----------------------------------------------

    def tokens_to_unique_class_values(self, x: torch.Tensor) -> torch.Tensor:
        if exists(self.unique_class_values):
            self.unique_class_values_tensor = self.unique_class_values_tensor.to(x.device)
            return torch.searchsorted(self.unique_class_values_tensor, x)
        return x

    def unique_class_values_to_tokens(self, x: torch.Tensor) -> torch.Tensor:
        if exists(self.unique_class_values):
            self.unique_class_values_tensor = self.unique_class_values_tensor.to(x.device)
            return self.unique_class_values_tensor[x]
        return x
    
    #-----------------------------------------------

    def embed_discrete(self, h: torch.Tensor) -> torch.Tensor:

        if self.unique_class_values:
            # tokens are already correct
            tokens = h 
            x_emb  = self.emb_clr(tokens)
        
        elif self.explicit_node_type_embeddings:
            # e.g. num_clrs=4: [-2, -1, zero, 1, 2, padd] to all positive  [0, 1, 2 (zero), 3, 4, 5 (padd)]
            tokens = h 
            x_emb  = self.emb_clr(tokens + (self.num_clrs-2))
        
        else:
            sign   = torch.sign(h + 0.1)  #trick: add 0.1 so that the sign of 0 is +1, else the 0 token would be all 0s.     
            tokens = torch.abs(h)
            
            x_emb = self.emb_clr(tokens)      
            x_emb = x_emb * sign.unsqueeze(-1)     # [b, s, t, ch]
        
        return x_emb, tokens
       

    def embed(self, h: torch.Tensor, w: torch.Tensor) -> torch.Tensor: 
        """
        sample from p(x0|h, w)
        h discrete
        w cont
        """

        x_emb, tokens = self.embed_discrete(h)

        v_p    = self.embed_continuous(w, tokens)          
        x_emb += v_p     

        if not self.channel_last:   
             # contiguous important for multi-node cluster     
            x_emb = torch.permute(x_emb, (0, 3, 1, 2)).contiguous() # to [b, ch, s, t]
     
        return x_emb
    
    #-----------------------------------------------

    def get_discrete_sim(self, x: torch.Tensor) -> torch.Tensor:
        #collaps clr to gate ... use cos sim
 
        clrs = self.emb_clr.weight.detach()[:self._num_discrete_embeddings] # is [clr_num, clr_dim]
        
        model_device = clrs.device
        x = x.to(model_device)
        
        # to shape [b*space*time, clr_dim]
        x_flat = x.reshape(-1, x.shape[-1])
                
        #normalize for cos sim       
        norm_clr    = F.normalize(  clrs[:, :self.clr_dim], dim=1) #clrs   / torch.linalg.vector_norm(  clrs, dim=1, keepdim=True) #torch.linalg.vector_norm(  clrs[:, :self.clr_dim], dim=1, keepdim=True) 
        norm_x_flat = F.normalize(x_flat[:, :self.clr_dim], dim=1) #x_flat / torch.linalg.vector_norm(x_flat, dim=1, keepdim=True) #torch.linalg.vector_norm(x_flat[:, :self.clr_dim], dim=1, keepdim=True) 
        
        #matmul out is [clr_num, b*space*time] =  [clr_num, clr_dim] x [b*space*time, clr_dim].T
        sim = torch.matmul(norm_clr, norm_x_flat.T) 

        return sim

    @torch.inference_mode()
    def invert_discrete(self, x: torch.Tensor, return_sim: bool = False, finite_temperature: bool = False) -> torch.Tensor:
        #collaps clr to gate ... use cos sim
 
        input_device = x.device

        if not self.channel_last:   
            x = x.permute(0, 2, 3, 1)
        
        #sim out is [clr_num, b*space*time]
        sim = self.get_discrete_sim(x)

        if self.explicit_node_type_embeddings or self.unique_class_values:
            #get highest similarity
            if finite_temperature:
                _cat = torch.distributions.categorical.Categorical(logits=sim.transpose(-1, -2))
                scores_flat = _cat.sample()
            else:
                scores_flat = torch.argmax(sim, dim=0) #reduce the clr_num dim

            if self.explicit_node_type_embeddings:
                scores_flat = scores_flat - (self.num_clrs-2)
            
        else:
            #get highest abs(similarity) and sign of it
            abs_sim = sim.abs()
            
            if finite_temperature:
                _cat = torch.distributions.categorical.Categorical(logits=abs_sim.transpose(-1, -2))
                max_idx = _cat.sample()
            else:
                max_idx = torch.argmax(abs_sim, dim=0) #reduce the clr_num dim
                
            sign = torch.sign(sim[max_idx, torch.arange(x_flat.shape[0])])
            scores_flat = max_idx * sign

        # back to [b, space, time]
        scores = scores_flat.reshape(x.shape[0], x.shape[1], x.shape[2]).to(torch.int64)      
        scores = scores.to(input_device)

        if return_sim:
            return scores, sim
        return scores

    @torch.inference_mode()
    def invert(self, x: torch.Tensor, reduce_spatial: bool = True) -> torch.Tensor: 
        """sample from p(h, w|x0)"""

        pred_tokens = self.invert_discrete(x)
        pred_params = self.invert_continuous(x, pred_tokens, reduce_spatial=reduce_spatial)

        pred_tokens = self.unique_class_values_to_tokens(pred_tokens)
        
        return pred_tokens, pred_params

    #-----------------------------------------------

    def _prepare_params(self, tokens: torch.Tensor, w: torch.Tensor) -> torch.Tensor:
        tokens = tokens.abs()

        # w ... [b, nP, s or 1, t]
        
        if self.parametrized_tokens:
            # Force all non parameterized embeddings to all zero or random lambdas !
            pmask = self.get_parametrized_mask(tokens).unsqueeze(1)     # [b, 1, s, t]     
            rnd_w = torch.zeros((w.shape[0], w.shape[1], pmask.shape[2], w.shape[3]), device=w.device)   
            w_m   = torch.where(pmask, w, rnd_w)
            
        else:
            # this does not include padding tokens!
            pmask = (tokens > 0).unsqueeze(1)
            w_m   = torch.where(pmask, w, 0.0) # ... [b, nP, s, t]
        
        return w_m

    def _reduce_params_spatial(self, tokens: torch.Tensor, params: torch.Tensor) -> torch.Tensor:
        tokens = tokens.abs()

        if self.parametrized_tokens:
            #check if not param gate
            mask = self.get_parametrized_mask(tokens).unsqueeze(1).float()  # ... [b, 1, s, t]
        else:
            #check if not empty token
            mask = (tokens > 0).unsqueeze(1).float() # ... [b, 1, s, t]

        # to catch all zero tokens at t, compute how many we have per timestep
        red_mask = mask.sum(-2) # ... [b, 1, t]
        red_mask = torch.where(red_mask > 0.0, red_mask, 1.0)
        
        params = (params*mask).sum(-2) / red_mask # ... [b, nP, s, t] to [b, nP, t]   average over s, ignore masked positions        
        return params

    def get_parametrized_mask(self, tokens: torch.Tensor) -> torch.Tensor:

        parametrized_tokens = torch.tensor(self.parametrized_tokens, device=tokens.device) 
        
        if exists(self.unique_class_values):
            parametrized_tokens = self.tokens_to_unique_class_values(parametrized_tokens)
  
        pmask = torch.isin(tokens.abs(), parametrized_tokens) 
  
        return pmask

# %% ../../../src/models/embedding/rotational_preset_embedder.ipynb 9
class RotationalMultimodialPresetEmbedder(MultimodialPresetEmbedder):
    
    def __init__(self, 
                 clr_dim: int, 
                 num_clrs: int, 
                 params_dim: int, 
                 num_params_per_clr: int, 
                 zero_sum_space: bool,
                 explicit_node_type_embeddings: bool = True,
                 channel_last: bool = True,
                 parametrized_tokens: Optional[list[int]] = None,
                 unique_class_values: Optional[list[int]] = None
                ) -> None:

        self.channel_last = channel_last
        self.parametrized_tokens = parametrized_tokens
        
        if (2*num_params_per_clr*num_clrs) > params_dim and num_params_per_clr > 0:
            print(f"[WARNING]: We need at least a `params_dim` (is {params_dim}) of `2*num_params_per_clr*num_clrs` (is {2*num_params_per_clr*num_clrs}),"
                  f" automatically setting `params_dim` to {2*num_params_per_clr*num_clrs} to inforce this!")
        
            params_dim = 2*num_params_per_clr*num_clrs

        if zero_sum_space and (2*num_params_per_clr*num_clrs+1) > params_dim and num_params_per_clr > 0:
            print(f"[WARNING]: `params_dim` is set to the minimum `2*num_params_per_clr*num_clrs`={2*num_params_per_clr*num_clrs},"
                  f" but for `{zero_sum_space=}` we need one more dimension, automatically setting it to"
                  f" `2*num_params_per_clr*num_clrs+1` {2*num_params_per_clr*num_clrs+1}.")
            
            params_dim = 2*num_params_per_clr*num_clrs + 1
            
        super().__init__(clr_dim=clr_dim,
                         num_clrs=num_clrs,
                         params_dim=params_dim,
                         num_params_per_clr=2*num_params_per_clr,  # pass factor 2 to create more embeddings for cos-sin encoding
                         zero_sum_space=zero_sum_space,
                         explicit_node_type_embeddings=explicit_node_type_embeddings,
                         channel_last=channel_last,
                         parametrized_tokens=parametrized_tokens,
                         unique_class_values=unique_class_values) 

        self.num_params_per_clr    = num_params_per_clr   # remove the factor 2
        self._num_param_embeddings = self.num_params_per_clr * self.num_clrs 
        self.nP                    = num_params_per_clr

        self.params_config = MultimodialPresetEmbedderConfig(clr_dim=self.clr_dim, 
                                                             num_clrs=self.num_clrs, 
                                                             params_dim=self.params_dim, 
                                                             num_params_per_clr=self.num_params_per_clr,
                                                             zero_sum_space=self.zero_sum_space,
                                                             explicit_node_type_embeddings=self.explicit_node_type_embeddings,
                                                             channel_last=self.channel_last,
                                                             parametrized_tokens=self.parametrized_tokens,
                                                             unique_class_values=self.unique_class_values)

    
    def embed_continuous(self, w: torch.Tensor, tokens: torch.Tensor) -> torch.Tensor:
        # take care that v_empty stays that! not apply params to all bits only to a [s,t] pos
        # params ... [b, nP, t]
        # w      ...  qc=[b, nP, t]     mbqc=[b, nP, s, t]

        tokens = tokens.abs()
        
        if w.dim() == 3:
            w = w.unsqueeze(2) # to [b, nP, 1, t]


        w_m = self._prepare_params(tokens, w)
        
        w_m = w_m.unsqueeze(-1)  # ... [b, nP, s, t, 1]
        w_m = w_m * torch.pi     # [-1, 1] to [-pi, pi]

        # first pick starting points of indices
        # then add a numerator for all the number of paramters
        # then add a numerator for cos-sin vectors
        
        #Note: .view(-1, 1, 1) introduces some numeric variances in 1e-07 range, but should be faster!
        indices = self._num_discrete_embeddings + tokens * self.nP * 2                                    # ... [b, s, t]    
        indices = indices.unsqueeze(1) + torch.arange(self.nP, device=indices.device).view(-1, 1, 1) * 2  # ... [b, nP, s, t]
        indices = indices.unsqueeze(1) + torch.arange(2, device=indices.device).view(-1, 1, 1, 1)         # ... [b, 2, nP, s, t] 
        p_clrs  = self.emb_clr(indices).contiguous()                                                      # ... [b, 2, nP, s, t, ch]
    
        v_p = torch.cos(w_m)*p_clrs[:, 0] + torch.sin(w_m)*p_clrs[:, 1] # ... [b, nP, s, t, ch]
        v_p = torch.sum(v_p, dim=1)                                     # ... [b, s, t, ch]

        return v_p

    @torch.inference_mode()
    def invert_continuous(self, x: torch.Tensor, tokens: torch.Tensor, reduce_spatial: bool = True) -> torch.Tensor:
        """reduce_spatial=True for circuits, False for mbqc"""
        
        model_device = self.emb_clr.weight.device
        input_device = x.device

        if not self.channel_last:
            x = x.permute(0, 2, 3, 1)   # to [b,    s, t, ch]
        x = x.unsqueeze(1).unsqueeze(1)  # to [b, 1, 1, s, t, ch]
      
        x      = x.to(model_device) 
        tokens = tokens.to(model_device).abs()

        #-----
        # params should [b, nP, max_gates]
        # x      ... [b, ch, s, t] 
        # tokens ... [b,   , s, t] 

        #Note: .view(-1, 1, 1) introduces some numeric variances in 1e-07 range, but should be faster!
        indices = self._num_discrete_embeddings + tokens * self.nP * 2                                    # ... [b, s, t]    
        indices = indices.unsqueeze(1) + torch.arange(self.nP, device=indices.device).view(-1, 1, 1) * 2  # ... [b, nP, s, t]
        indices = indices.unsqueeze(1) + torch.arange(2, device=indices.device).view(-1, 1, 1, 1)         # ... [b, 2, nP, s, t] 
        p_clrs  = self.emb_clr(indices).contiguous()                                                      # ... [b, 2, nP, s, t, ch]

        overlaps = (x * p_clrs).sum(-1)                           # ... [b, 2, nP, s, t]
        params   = torch.arctan2(overlaps[:, 1], overlaps[:, 0])  # ... [b, nP, s, t]
        params   = params / torch.pi                              #  [-pi, pi] to [-1, 1]
           
        # now reduce spatial s, average over non empty token s
        if reduce_spatial:
            params = self._reduce_params_spatial(tokens, params)
               
        return params.to(input_device)

# %% ../../../src/models/embedding/rotational_preset_embedder.ipynb 12
class RotationalMultimodialPresetEmbedderTiny(MultimodialPresetEmbedder):
    """Mostly the same as `RotationalMultimodialPresetEmbedder`, but the param embedding is not depending on the tokens."""
    
    def __init__(self, 
                 clr_dim: int, 
                 num_clrs: int,
                 params_dim: int, 
                 num_params_per_clr: int, 
                 zero_sum_space: bool,
                 explicit_node_type_embeddings: bool = True,
                 channel_last: bool = True,
                 parametrized_tokens: Optional[list[int]] = None,
                 unique_class_values: Optional[list[int]] = None
                ) -> None:
        super(MultimodialPresetEmbedder, self).__init__(zero_sum_space=zero_sum_space) # call grandparent class

        if exists(unique_class_values):
            assert isinstance(unique_class_values, list)
            self.unique_class_values_tensor = torch.tensor(unique_class_values)
            
            explicit_node_type_embeddings = False

            print(f"[INFO]: provided `unique_class_values` ({unique_class_values}), enforcing `num_clrs=len(unique_class_values)={len(unique_class_values)}`.")
            num_clrs = len(unique_class_values)
        
        self.zero_sum_space = zero_sum_space
        self.explicit_node_type_embeddings = explicit_node_type_embeddings  
        self.channel_last = channel_last
        self.parametrized_tokens = parametrized_tokens
        self.unique_class_values = unique_class_values
        # assert exists(parametrized_tokens)

        if (2*num_params_per_clr) > params_dim and num_params_per_clr > 0:
            print(f"[WARNING]: We need at least a `params_dim` (is {params_dim}) of `2*num_params_per_clr` (is {2*num_params_per_clr}),"
                  f" automatically setting `params_dim` to {2*num_params_per_clr} to inforce this!")
        
            params_dim = 2*num_params_per_clr

        if self.zero_sum_space and (2*num_params_per_clr+1) > params_dim and num_params_per_clr > 0:
            print(f"[WARNING]: `params_dim` is set to the minimum `2*num_params_per_clr`={2*num_params_per_clr},"
                  f" but for `{zero_sum_space=}` we need one more dimension, automatically setting it to"
                  f" `2*num_params_per_clr+1` {2*num_params_per_clr+1}.")
            
            params_dim = 2*num_params_per_clr + 1
       
        if self.zero_sum_space:
            if self.explicit_node_type_embeddings and ((num_clrs*2 - 2) + 1) > clr_dim:
                print(f"[WARNING]: `clr_dim` is set to {clr_dim} and `{explicit_node_type_embeddings=}`,"
                      f" but for `{zero_sum_space=}` we need one more dimension than the number of tokens `(num_clrs*2 - 2)` (is {(num_clrs*2 - 2)}),"
                      f" automatically setting it to `clr_dim=(num_clrs*2 - 2) + 1` {(num_clrs*2 - 2) + 1}.")

                # has empty and padd tokens, these only have the plus branch (so -2)!
                clr_dim = (num_clrs*2 - 2) + 1

            elif (num_clrs + 1) > clr_dim:
                print(f"[WARNING]: `clr_dim` is set to {clr_dim} and `{explicit_node_type_embeddings=}`,"
                      f" but for `{zero_sum_space=}` we need one more dimension than the number of tokens `num_clrs` (is {num_clrs}),"
                      f" automatically setting it to `clr_dim=num_clrs+1` {num_clrs+1}.")
                
                clr_dim = num_clrs + 1
  
        self.clr_dim            = clr_dim
        self.num_clrs           = num_clrs
        self.params_dim         = params_dim
        self.num_params_per_clr = num_params_per_clr
        self.nP                 = num_params_per_clr
     
        self._num_discrete_embeddings = self.num_clrs
        self._num_param_embeddings    = self.num_params_per_clr * 2
        self.embedding_dim            = self.clr_dim + self.params_dim
       
        if self.explicit_node_type_embeddings:
            # use distinct embeddings for +-k and not just +-v
            # has empty and padd tokens, these only have the plus branch (so -2)!
            self._num_discrete_embeddings = self.num_clrs*2 - 2
            
        self.num_embeddings = self._num_discrete_embeddings + self._num_param_embeddings 
        self.emb_clr        = nn.Embedding(num_embeddings=self.num_embeddings, embedding_dim=self.embedding_dim)    
        print(f"[INFO]: Created `nn.Embedding` with a total of {self.num_embeddings} vectors in a {self.embedding_dim} dimensional space.")
        
        self.params_config = MultimodialPresetEmbedderConfig(clr_dim=self.clr_dim, 
                                                             num_clrs=self.num_clrs, 
                                                             params_dim=self.params_dim, 
                                                             num_params_per_clr=self.num_params_per_clr,
                                                             zero_sum_space=self.zero_sum_space,
                                                             explicit_node_type_embeddings=self.explicit_node_type_embeddings,
                                                             channel_last=self.channel_last,
                                                             parametrized_tokens=self.parametrized_tokens,
                                                             unique_class_values=self.unique_class_values)
        
        self._init_weights(zero_sum_space=self.zero_sum_space)

    def embed_continuous(self, w: torch.Tensor, tokens: torch.Tensor) -> torch.Tensor:
        # take care that v_empty stays that! not apply params to all bits only to a [s,t] pos
        # params ... [b, nP, t]
        # w      ...  qc=[b, nP, t]     mbqc=[b, nP, s, t]

        tokens = tokens.abs()
        
        if w.dim() == 3:
            w = w.unsqueeze(2) # to [b, nP, 1, t]

        w_m = self._prepare_params(tokens, w)
            
        w_m = w_m.unsqueeze(-1)  # ... [b, nP, s, t, 1]
        w_m = w_m * torch.pi     # [-1, 1] to [-pi, pi]

        # first pick starting points of indices
        # then add a numerator for all the number of paramters
        # then add a numerator for cos-sin vectors
        
        #Note: .view(-1, 1, 1) introduces some numeric variances in 1e-07 range, but should be faster!
        indices = torch.full_like(tokens, self._num_discrete_embeddings)   #+ 0 * tokens * self.nP * 2                               # ... [b, s, t]    
        indices = indices.unsqueeze(1) + torch.arange(self.nP, device=indices.device).view(-1, 1, 1) * 2  # ... [b, nP, s, t]
        indices = indices.unsqueeze(1) + torch.arange(2, device=indices.device).view(-1, 1, 1, 1)         # ... [b, 2, nP, s, t] 
        p_clrs  = self.emb_clr(indices).contiguous()                                                      # ... [b, 2, nP, s, t, ch]

        # This cos-sin combination conserves mean and variance of the embeddings
        v_p = torch.cos(w_m)*p_clrs[:, 0] + torch.sin(w_m)*p_clrs[:, 1] # ... [b, nP, s, t, ch]
        v_p = torch.sum(v_p, dim=1)                                     # ... [b, s, t, ch]

        return v_p

    @torch.inference_mode()
    def invert_continuous(self, x: torch.Tensor, tokens: torch.Tensor, reduce_spatial: bool = True) -> torch.Tensor:
        """reduce_spatial=True for circuits, False for mbqc"""
        
        model_device = self.emb_clr.weight.device
        input_device = x.device

        if not self.channel_last:
            x = x.permute(0, 2, 3, 1)   # to [b,    s, t, ch]
        x = x.unsqueeze(1).unsqueeze(1)  # to [b, 1, 1, s, t, ch]
      
        x      = x.to(model_device) 
        tokens = tokens.to(model_device).abs()

        #-----
        # params should [b, nP, max_gates]
        # x      ... [b, ch, s, t] 
        # tokens ... [b,   , s, t] 

        #Note: .view(-1, 1, 1) introduces some numeric variances in 1e-07 range, but should be faster!
        indices = torch.full_like(tokens, self._num_discrete_embeddings) #+ 0 * tokens * self.nP * 2                                               # ... [b, s, t]    
        indices = indices.unsqueeze(1) + torch.arange(self.nP, device=indices.device).view(-1, 1, 1) * 2  # ... [b, nP, s, t]
        indices = indices.unsqueeze(1) + torch.arange(2, device=indices.device).view(-1, 1, 1, 1)         # ... [b, 2, nP, s, t] 
        p_clrs  = self.emb_clr(indices).contiguous()                                                      # ... [b, 2, nP, s, t, ch]

        # Note we dont need to normalize x as this norm cancels in  the fraction of arctan2(y/x)
        overlaps = (x * p_clrs).sum(-1)                           # ... [b, 2, nP, s, t]
        params   = torch.arctan2(overlaps[:, 1], overlaps[:, 0])  # ... [b, nP, s, t]
        params   = params / torch.pi                              #  [-pi, pi] to [-1, 1]
           
        # now reduce spatial s, average over non empty token s
        if reduce_spatial:
            params = self._reduce_params_spatial(tokens, params)

        return params.to(input_device)
