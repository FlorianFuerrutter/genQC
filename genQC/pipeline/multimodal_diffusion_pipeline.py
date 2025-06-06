"""Multimodal extension to `DiffusionPipeline`."""

# AUTOGENERATED! DO NOT EDIT! File to edit: ../../src/pipeline/multimodal_diffusion_pipeline.ipynb.

# %% auto 0
__all__ = ['MultimodalDiffusionPipeline_ParametrizedCompilation']

# %% ../../src/pipeline/multimodal_diffusion_pipeline.ipynb 2
from ..imports import *
from .compilation_diffusion_pipeline import DiffusionPipeline_Compilation

from ..scheduler.scheduler import Scheduler
from ..utils.config_loader import *
from ..models.config_model import ConfigModel

# %% ../../src/pipeline/multimodal_diffusion_pipeline.ipynb 4
class MultimodalDiffusionPipeline_ParametrizedCompilation(DiffusionPipeline_Compilation):   
    """A special `DiffusionPipeline_Compilation` that accounts for multimodal parametrized gates."""

    def __init__(self, *args, scheduler_w, **kwargs):
        super().__init__(*args, **kwargs)
        self.scheduler_w = scheduler_w
        self.scheduler_w.to(self.device) 

    def params_config(self, *args, **kwargs):
        params_config = super().params_config(*args, **kwargs)
        params_config["scheduler_w"] = self.scheduler_w.get_config()
        return params_config

    @staticmethod
    def from_config_file(config_path, device: torch.device, save_path: Optional[str] = None):    
        config = load_config(config_path+"config.yaml")   
        config = config_to_dict(config)

        def _get_save_path(config_save_path, appendix):

            _save_path = default(save_path, config_path) + appendix
            if "save_path" in config_save_path:
                if exists(config_save_path["save_path"]):
                    _save_path = config_save_path["save_path"]
                else:
                    config_save_path.pop("save_path")
            return _save_path    
        
        if exists(device):
            config["params"]["device"]                        = device
            config["params"]["scheduler"]["params"]["device"] = device
        
        config["params"]["scheduler"]   = Scheduler.from_config(config["params"]["scheduler"]  , device, _get_save_path(config["params"]["scheduler"]  , ""))
        config["params"]["scheduler_w"] = Scheduler.from_config(config["params"]["scheduler_w"], device, _get_save_path(config["params"]["scheduler_w"], ""))
        
        config["params"]["model"] = ConfigModel.from_config(config["params"]["model"], device, _get_save_path(config["params"]["model"], "model"))
        config["params"]["text_encoder"] = ConfigModel.from_config(config["params"]["text_encoder"], device, _get_save_path(config["params"]["text_encoder"], "text_encoder")) 
        config["params"]["embedder"] = ConfigModel.from_config(config["params"]["embedder"], device, _get_save_path(config["params"]["embedder"], "embedder"))  
        
        add_config = config["params"].pop("add_config", None)

        pipeline = instantiate_from_config(config)
        
        if exists(pipeline.add_config):
            pipeline.add_config = add_config
            
            params = add_config["dataset"]["params"]
            
            if "gate_pool" in params: 
                # pipeline.gate_pool = [get_obj_from_str(gate) for gate in params["gate_pool"]] 
                pipeline.gate_pool = [gate for gate in params["gate_pool"]] 

        return pipeline
    
    #------------------------------------

    # @torch.no_grad()
    @torch.inference_mode()
    def denoising(self, latents, c, U, negative_c=None, negative_u=None, enable_guidance=True, g=1.0, t_start_index=0, no_bar=False, return_predicted_x0=False):
        return super().denoising(latents=latents, c=c, U=U, negative_c=negative_c, negative_u=negative_u, enable_guidance=enable_guidance, g=g, t_start_index=t_start_index,
                                 no_bar=no_bar, return_predicted_x0=return_predicted_x0)

    #------------------------------------

    sample_type = "joint"
    
    def denoising_step(self, 
                       latents: torch.Tensor, 
                       ts: Union[int, torch.IntTensor], 
                       c_emb: torch.Tensor = None, 
                       enable_guidance = False, 
                       g: float = 7.5, 
                       U: torch.Tensor = None,
                      **kwargs) -> Tuple[torch.Tensor, torch.Tensor]: 

        match self.sample_type:
            case "joint":
                x_tm1, x0 = self.denoising_step_joint(latents, ts, c_emb, enable_guidance, g, U)

            case "w":
                # Here the single mode denoising functions
                x_tm1, x0 = self.denoising_step_single_mode_w(latents, ts, c_emb, enable_guidance, g, U)

            case _:
                raise NotImplementedError("")
        
        return x_tm1, x0

    #------------------------------------
    # Cleaned steps

    def _get_guidance_scales(self, g: float, ts_h: torch.Tensor, ts_w: torch.Tensor):
        g_h     , g_w      = g, g
        lambda_h, lambda_w = g, g
        
        if hasattr(self, "g_h"): 
            if isinstance(self.g_h, Callable):
                assert ts_h.numel() == 1
                g_h = self.g_h(ts_h)
            else:
                g_h = self.g_h
        
        if hasattr(self, "g_w"):       
            if isinstance(self.g_w, Callable): 
                assert ts_w.numel() == 1
                g_w = self.g_w(ts_w)
            else:
                g_w = self.g_w

        if hasattr(self, "lambda_h"): 
            if isinstance(self.lambda_h, Callable):
                assert ts_h.numel() == 1
                lambda_h = self.lambda_h(ts_h)
            else:
                lambda_h = self.lambda_h
    
        if hasattr(self, "lambda_w"):       
            if isinstance(self.lambda_w, Callable): 
                assert ts_w.numel() == 1
                lambda_w = self.lambda_w(ts_w)
            else:
                lambda_w = self.lambda_w
        
        return g_h, g_w, lambda_h, lambda_w

    def denoising_step_joint(self, 
                             latents: torch.Tensor, 
                             ts: Union[int, torch.IntTensor], 
                             c_emb: torch.Tensor = None, 
                             enable_guidance = False, 
                             g: float = 7.5, 
                             U: torch.Tensor = None,
                            ) -> Tuple[torch.Tensor, torch.Tensor]:

        # Prepare variables
        g_h, g_w, lambda_h, lambda_w = self._get_guidance_scales(g, ts_h=ts, ts_w=ts)

        # assert enable_guidance
        c_emb_u, c_emb_c = c_emb.chunk(2)
        U_u    , U_c     = U.chunk(2)

        ts_expanded = ts.expand(latents.shape[0])
        T_h_expanded = torch.ones_like(ts_expanded) * (self.scheduler.num_train_timesteps-1)
        T_w_expanded = torch.ones_like(ts_expanded) * (self.scheduler_w.num_train_timesteps-1)

        # Get latents of modes
        noisy_latents = torch.randn_like(latents)
        latents_h,             latents_w =       latents[..., :self.embedder.clr_dim],       latents[..., self.embedder.clr_dim:]
        noisy_latents_h, noisy_latents_w = noisy_latents[..., :self.embedder.clr_dim], noisy_latents[..., self.embedder.clr_dim:]
        
        # Get all combinations
        latents_chunked_h = torch.cat([
            latents_h, # sh_h
            latents_h, # sh_hw
            latents_h, # sh_hwc

            noisy_latents_h, # sw_w
            latents_h, # sw_hw
            latents_h, # sw_hwc       
        ])
    
        latents_chunked_w = torch.cat([
            noisy_latents_w, # sh_h
            latents_w, # sh_hw
            latents_w, # sh_hwc

            latents_w, # sw_w
            latents_w, # sw_hw
            latents_w, # sw_hwc       
        ])

        t_h_chunked = torch.cat([
            ts_expanded, # sh_h
            ts_expanded, # sh_hw
            ts_expanded, # sh_hwc

            T_h_expanded, # sw_w
            ts_expanded, # sw_hw
            ts_expanded, # sw_hwc       
        ])

        t_w_chunked = torch.cat([
            T_w_expanded, # sh_h
            ts_expanded, # sh_hw
            ts_expanded, # sh_hwc

            ts_expanded, # sw_w
            ts_expanded, # sw_hw
            ts_expanded, # sw_hwc       
        ])

        c_emb_chunked = torch.cat([
            c_emb_u, # sh_h
            c_emb_u, # sh_hw
            c_emb_c, # sh_hwc

            c_emb_u, # sw_w
            c_emb_u, # sw_hw
            c_emb_c, # sw_hwc       
        ])

        U_chunked = torch.cat([
            U_u, # sh_h
            U_u, # sh_hw
            U_c, # sh_hwc

            U_u, # sw_w
            U_u, # sw_hw
            U_c, # sw_hwc       
        ])

        # Make all predictions we need
        latents_chunked = torch.cat([latents_chunked_h, latents_chunked_w], dim=-1)
        
        pred = self.model(latents_chunked, t_h=t_h_chunked, t_w=t_w_chunked, c_emb=c_emb_chunked, U=U_chunked)
        pred_h, pred_w = pred[..., :self.embedder.clr_dim], pred[..., self.embedder.clr_dim:]
        
        sh_h, sh_hw, sh_hwc, _, _, _ = pred_h.chunk(6)
        _, _, _, sw_w, sw_hw, sw_hwc = pred_w.chunk(6)
        
        # Combine into CFG   
        sh_bar = sh_h + g_h * (sh_hw - sh_h) + lambda_h * (sh_hwc - sh_hw)
        sw_bar = sw_w + g_w * (sw_hw - sw_w) + lambda_w * (sw_hwc - sw_hw)
        
        # Do denoise step with CFG++
        x_h = self.scheduler.step(sh_bar, ts, latents_h, uncond_model_output=sh_h)  
        x_w = self.scheduler_w.step(sw_bar, ts, latents_w, uncond_model_output=sw_w)  
        
        return torch.cat([x_h.prev_sample, x_w.prev_sample], dim=-1), torch.cat([x_h.pred_original_sample, x_w.pred_original_sample], dim=-1)
    
    #------------------------------------

    def denoising_step_single_mode_w(self,
                                     latents: torch.Tensor,
                                     ts: Union[int, torch.IntTensor], 
                                     c_emb: torch.Tensor = None,
                                     enable_guidance = False, 
                                     g: float = 7.5, 
                                     U: torch.Tensor = None
                                    ) -> Tuple[torch.Tensor, torch.Tensor]:

        assert enable_guidance  # TODO: remove this

        chunk_latents = torch.cat([latents] * 2, dim=0)
        
        if ts.numel() > 1: chunk_ts = torch.cat([ts] * 2, dim=0)
        else:              chunk_ts = ts

        T     = torch.ones_like(chunk_ts) * (self.scheduler.num_train_timesteps-1)
        TZero = torch.zeros_like(chunk_ts) 
        
        #------------------------
        # 1. Get:  s(h|w), s(w|h)   and   s(h|w,c), s(w|h,c)
        # Note here we set t_h=0
        
        def f1(chunk_latents, chunk_ts):
            x = chunk_latents.clone()
            
            s_hw, s_hwc = self.model(x, t_h=TZero, t_w=chunk_ts, c_emb=c_emb, U=U).chunk(2) 
    
            sw_hw, sw_hwc = s_hw[..., self.embedder.clr_dim:], s_hwc[..., self.embedder.clr_dim:]
            
            return sw_hw, sw_hwc
                  
        #------------------------
        # 2. Get: s(w), s(w|c)

        def f2(chunk_latents, chunk_ts):
            x = chunk_latents.clone()
            x[..., :self.embedder.clr_dim] = torch.randn_like(x[..., :self.embedder.clr_dim]) #remove h
    
            s_w, s_wc = self.model(x, t_h=T, t_w=chunk_ts, c_emb=c_emb, U=U).chunk(2) 
    
            sw_w, sw_wc = s_w[..., self.embedder.clr_dim:], s_wc[..., self.embedder.clr_dim:]

            return sw_w, sw_wc
            
        #------------------------------------------------

        sw_hw, sw_hwc = f1(chunk_latents, chunk_ts)
        sw_w, sw_wc   = f2(chunk_latents, chunk_ts)

        g_w = g
               
        if hasattr(self, "g_w"):       
            if isinstance(self.g_w, Callable): 
                assert ts.numel() == 1
                g_w = self.g_w(chunk_ts)
            else:
                g_w = self.g_w
      
        gamma_w  = g_w  #was no/2
        lambda_w = g_w

        if hasattr(self, "lambda_w"):       
            if isinstance(self.lambda_w, Callable): 
                assert ts.numel() == 1
                lambda_w = self.lambda_w(chunk_ts)
            else:
                lambda_w = self.lambda_w

        sw_bar = sw_w + gamma_w * (sw_hw - sw_w) + lambda_w * (sw_hwc - sw_hw)

        latents_h, latents_w = latents[..., :self.embedder.clr_dim], latents[..., self.embedder.clr_dim:]
        
        #CFG++
        x_h = latents_h
        x_w = self.scheduler_w.step(sw_bar, ts, latents_w, uncond_model_output=sw_w)  

        return torch.cat([x_h, x_w.prev_sample], dim=-1), torch.cat([x_h, x_w.pred_original_sample], dim=-1)

    #------------------------------------
    
    def train_step(self, data, train, **kwargs): 
        target_tokens, y, params, U = data                
        b, s, t = target_tokens.shape          

        #start async memcpy
        target_tokens = target_tokens.to(self.device, non_blocking=self.non_blocking)  
        params        = params.to(self.device, non_blocking=self.non_blocking)  
        
        latents  = self.embedder(h=target_tokens, w=params) 

        #do the cond embedding with CLIP   
        U = U.to(torch.float32)
        
        y = y.to(self.device, non_blocking=self.non_blocking)  
        U = U.to(self.device, non_blocking=self.non_blocking)  
        
        if self.enable_guidance_train and train:  #CFG training
            rnd = torch.empty((b,), device=self.device).bernoulli_(p=1.0-self.guidance_train_p).type(torch.int64)

            y_drop = self.cfg_drop(y, self.empty_token_fn(y)  , rnd) 
            U_drop = self.cfg_drop(U, self.empty_unitary_fn(U), rnd) 
                 
        else:
            rnd = torch.ones((b,), dtype=torch.int64, device=self.device)
            y_drop, U_drop = y, U
        
        y_emb = self.text_encoder(y_drop, pool=False)
   
        #--------------------

        shuffle = torch.tensor(0, dtype=bool).bernoulli_(p=0.95)
         
        timesteps_h = self.sample_timesteps_low_variance(b, self.scheduler)
        timesteps_w = self.sample_timesteps_low_variance(b, self.scheduler_w, shuffle=shuffle)

       
        noise = torch.randn_like(latents)  
        noisy_latents_h = self.scheduler.add_noise(  latents[..., :self.embedder.clr_dim], noise[..., :self.embedder.clr_dim], timesteps_h, train=train) 
        noisy_latents_w = self.scheduler_w.add_noise(latents[..., self.embedder.clr_dim:], noise[..., self.embedder.clr_dim:], timesteps_w, train=train)
 
        noisy_latents = torch.cat([noisy_latents_h, noisy_latents_w], dim=-1)

        #--------------------  
        model_output = self.model(x=noisy_latents, t_h=timesteps_h, t_w=timesteps_w, c_emb=y_emb, U=U_drop, rnd=rnd)
       
        #--------------------

        if self.scheduler.prediction_type == "epsilon":
            pred_target = noise
            raise NotImplementedError()

        elif self.scheduler.prediction_type == "v-type":
            alphas_cumprod_h = self.scheduler.unsqueeze_vector_to_shape(self.scheduler.alphas_cumprod[timesteps_h], latents.shape)
            alphas_cumprod_w = self.scheduler_w.unsqueeze_vector_to_shape(self.scheduler_w.alphas_cumprod[timesteps_w], latents.shape)

            pred_target_h = alphas_cumprod_h.sqrt() * noise[..., :self.embedder.clr_dim] - (1-alphas_cumprod_h).sqrt() * latents[..., :self.embedder.clr_dim]
            pred_target_w = alphas_cumprod_w.sqrt() * noise[..., self.embedder.clr_dim:] - (1-alphas_cumprod_w).sqrt() * latents[..., self.embedder.clr_dim:]
            
        else:
            raise NotImplementedError(f"{self.scheduler.prediction_type} does is not implemented for {self.__class__}")
            
        #--------------------
      
        t_h = timesteps_h / (self.scheduler.num_train_timesteps-1)
        # t_h = torch.sin(t_h*(torch.pi/2))**2 
        # t_h = torch.sin(t_h*(torch.pi/2))
        # -> else linear
           
        t_h = self.scheduler.unsqueeze_vector_to_shape(t_h, latents.shape)
        SNR_h = (1.0-t_h) / (t_h+1e-8) + 1e-8     # flip prob to snr
        mse_loss_weight_h = (1.0 - alphas_cumprod_h) * F.sigmoid(SNR_h.log())

        SNR_w = alphas_cumprod_w / (1.0-alphas_cumprod_w+1e-8) + 1e-8

        #comp mse
        mse_flat = lambda out, target: (out-target).square().mean(dim=list(range(1, len(out.shape))))
        loss_h = mse_flat(model_output[..., :self.embedder.clr_dim], pred_target_h.detach()) * mse_loss_weight_h.squeeze().detach()
        loss_w = mse_flat(model_output[..., self.embedder.clr_dim:], pred_target_w.detach()) * mse_loss_weight_w.squeeze().detach()
 
        loss = loss_h.mean() + loss_w.mean()
        return loss
