# AUTOGENERATED! DO NOT EDIT! File to edit: ../../src/models/unet_qc.ipynb.

# %% auto 0
__all__ = ['UNet_block', 'Encoder', 'Decoder', 'QC_Cond_UNet_config', 'QC_Cond_UNet', 'QC_Compilation_UNet_config',
           'QC_Compilation_UNet']

# %% ../../src/models/unet_qc.ipynb 3
from ..imports import *
from .config_model import ConfigModel
import genQC.models.layers as layers
import genQC.models.transformers.transformers as transformers
from .unitary_encoder import Unitary_encoder, Unitary_encoder_config

# %% ../../src/models/unet_qc.ipynb 5
class UNet_block(nn.Module):
    """The basic block of the U-Net. Is conditioned via cross-attention in `SpatialTransformer` and addition of the time ebedding in `ResBlock2D_Conditional`."""
    def __init__(self, ch_in, ch_out, t_emb_size, cond_emb_size, num_heads=8, num_res_blocks=1, transformer_depth=1):
        super().__init__()
                                
        self.resBlocks = nn.ModuleList() 
        for i in range(num_res_blocks):          
            self.resBlocks.append(layers.ResBlock2DConditional(ch_in, ch_out, t_emb_size, kernel_size=(1, 3)))
            ch_in = ch_out 
            
        self.transformer_depth = transformer_depth
        if self.transformer_depth > 0:
            self.spatialTransformer = transformers.SpatialTransformer(ch_out, cond_emb_size, num_heads, transformer_depth)
                   
        self._init_weights()
          
    def _init_weights(self):
        for resBlock in self.resBlocks:
            resBlock.conv2.weight.data.zero_() 
                      
    def forward(self, x, t_emb, c_emb, attn_mask, key_padding_mask):
        for resBlock in self.resBlocks:
            x = resBlock(x, t_emb)
        
        if self.transformer_depth > 0:
            x = self.spatialTransformer(x, c_emb, attn_mask, key_padding_mask)   
            
        return x

# %% ../../src/models/unet_qc.ipynb 6
class Encoder(nn.Module):
    """Encoder definition of the U-Net."""
    
    def __init__(self, model_features, t_emb_size, cond_emb_size, num_heads, num_res_blocks, transformer_depths):
        super().__init__()
        self.enc_blocks = nn.ModuleList() 
        
        in_ch = model_features[0]
        for model_feature,heads,res_blocks,transformer_depth in zip(model_features[1:-1], num_heads[:-1], num_res_blocks[:-1], transformer_depths[:-1]):
            out_ch         = model_feature            
            enc_block      = UNet_block(in_ch, out_ch, t_emb_size, cond_emb_size, heads, res_blocks, transformer_depth)            
            enc_block.down = layers.DownBlock2D(out_ch, out_ch, kernel_size=(1, 2), stride=(1, 2), padding=(0,0))       
            in_ch          = out_ch 
        
            self.enc_blocks.append(enc_block)
    
        self.mid_block = UNet_block(in_ch, model_features[-1], t_emb_size, cond_emb_size, num_heads[-1], num_res_blocks[-1], transformer_depths[-1])  # should be!
        
    def forward(self, x, t_emb, c_emb, attn_mask=None, key_padding_mask=None):        
        ftrs = []       
        for i,enc_block in enumerate(self.enc_blocks):
            x = enc_block(x, t_emb, c_emb, attn_mask[i], key_padding_mask[i])  # attn_mask only in first layer!

            ftrs.append(x)  
            x = enc_block.down(x)
    
        x = self.mid_block(x, t_emb, c_emb, attn_mask[-1], key_padding_mask[-1])
        ftrs.append(x)
        
        return ftrs

# %% ../../src/models/unet_qc.ipynb 7
class Decoder(nn.Module):
    """Decoder definition of the U-Net."""
    
    def __init__(self, model_features, t_emb_size, cond_emb_size, num_heads, num_res_blocks, transformer_depths):
        super().__init__()
        self.dec_blocks = nn.ModuleList()
                     
        in_ch = model_features[0]
        for model_feature,heads,res_blocks, transformer_depth in zip(model_features[1:], num_heads[1:], num_res_blocks[1:], transformer_depths[1:]):
            out_ch       = model_feature           
            dec_block    = UNet_block(out_ch*2, out_ch, t_emb_size, cond_emb_size, heads, res_blocks, transformer_depth)            
            dec_block.up = layers.UpBlock2D(in_ch, out_ch, kernel_size=(1, 2), stride=(1, 2), padding=(0,0))                          
            in_ch        = out_ch 
            
            self.dec_blocks.append(dec_block) 
                          
    def forward(self, x, encoder_features, t_emb, c_emb, attn_mask=None, key_padding_mask=None): 
        for i,(dec_block, ftr) in enumerate(zip(self.dec_blocks, encoder_features)):         
            x = dec_block.up(x)
            x = torch.cat([x, ftr / (2.0**0.5)], dim=1)
            
            x = dec_block(x, t_emb, c_emb, attn_mask[i], key_padding_mask[i])                                
        return x

# %% ../../src/models/unet_qc.ipynb 9
@dataclass
class QC_Cond_UNet_config:  
    model_features: list[int]
    clr_dim: int
    num_clrs: int
    t_emb_size: int  
    cond_emb_size: int
    num_heads: list[int]
    num_res_blocks: list[int]
    transformer_depths: list[int]

# %% ../../src/models/unet_qc.ipynb 10
class QC_Cond_UNet(ConfigModel):
    """Conditional U-Net model for quantum circuits. Implemets `embedd_clrs` and `invert_clr` functions to embed and decode color-tensors."""

    channel_last = False
    
    def __init__(self, model_features=[32,32,64], clr_dim=8, num_clrs=8, t_emb_size=128, cond_emb_size=512, 
                 num_heads=[8,8,2], num_res_blocks=[2, 2, 4], transformer_depths=[1,2,1]):
        
        super().__init__()       

        self.clr_dim  = clr_dim     
        self.num_clrs = num_clrs
        
        self.t_emb_size    = model_features[0] * 4 if not t_emb_size else t_emb_size
        self.cond_emb_size = model_features[0] * 4 if not cond_emb_size else cond_emb_size
            
        self.params_config = QC_Cond_UNet_config(model_features, self.clr_dim, self.num_clrs, self.t_emb_size, self.cond_emb_size, num_heads, num_res_blocks, transformer_depths)
            
        #-----------    
                             
        self.enc_chs = [model_features[0]] + list(model_features)
        self.dec_chs = list(model_features)[::-1]
        
        #-----------
                
        self.t_emb   = layers.TimeEmbedding(d_model=self.t_emb_size)
        self.emb_clr = nn.Embedding(num_embeddings=self.num_clrs, embedding_dim=self.clr_dim)           
        
        self.conv_in = nn.Conv2d(self.clr_dim, model_features[0], kernel_size=1, stride=1, padding ="same") #was kernel_size=3
        self.pos_enc = layers.PositionalEncoding2D(d_model=model_features[0])

        self.encoder = Encoder(self.enc_chs, self.t_emb_size, cond_emb_size=self.cond_emb_size, num_heads=num_heads, num_res_blocks=num_res_blocks, transformer_depths=transformer_depths)
        self.decoder = Decoder(self.dec_chs, self.t_emb_size, cond_emb_size=self.cond_emb_size, num_heads=num_heads[::-1], num_res_blocks=num_res_blocks[::-1], transformer_depths=transformer_depths[::-1])
        self.head    = nn.Conv2d(self.dec_chs[-1], self.clr_dim, kernel_size=1, stride=1, padding ="same")
                                               
        self._init_weights()
          
    def _init_weights(self):
        self.emb_clr.weight.requires_grad = False
        nn.init.orthogonal_(self.emb_clr.weight.data)
        
        for enc_block in self.encoder.enc_blocks:
            nn.init.orthogonal_(enc_block.down.conv1.weight)
        
        for dec_block in self.decoder.dec_blocks:
            nn.init.orthogonal_(dec_block.up.conv1.weight)
        
        self.head.weight.data.zero_()
       
    #--------------------------------------------
    
    def embed(self, x):
        sign = torch.sign(x + 0.1)  #trick: add 0.1 so that the sign of 0 is +1, else the 0 token would be all 0s.     
        clr  = self.emb_clr(torch.abs(x))      
        x = clr * sign[:, :, :, None]        
        x = torch.permute(x, (0, 3, 1, 2))       
        return x
    
    @torch.no_grad()
    def invert(self, x):
        #collaps clr to gate ... use cos sim
        
        clrs = self.emb_clr.weight.detach() # is [clr_num, clr_dim]
        
        model_device = clrs.device
        input_device = x.device
        
        # to shape [b*space*time, clr_dim]
        x      = x.to(model_device)
        x_flat = x.permute(0, 2, 3, 1).reshape(-1, x.shape[1])
                         
        #normlize for cos sim       
        norm_clr    = clrs   / torch.linalg.vector_norm(  clrs, dim=1, keepdim=True) 
        norm_x_flat = x_flat / torch.linalg.vector_norm(x_flat, dim=1, keepdim=True) 
        
        #matmul out is [clr_num, b*space*time]
        sim = torch.matmul(norm_clr, norm_x_flat.T) 
            
        #get highest abs(similarity) and sign of it
        abs_sim = sim.abs()
        max_idx = torch.argmax(abs_sim, dim=0) #reduce the clr_num dim
        sign = torch.sign(sim[max_idx, torch.arange(x_flat.shape[0])])
        scores_flat = max_idx * sign

        # back to [b, space, time]
        scores = scores_flat.reshape(x.shape[0], x.shape[2], x.shape[3]).to(torch.int64)      
        scores = scores.to(input_device)
        
        return scores
    
    #--------------------------------------------
    
    def forward(self, x, t, c_emb, attn_mask=None, key_padding_mask=None, **kwargs):
        if attn_mask        is None: attn_mask        = [None] * len(self.enc_chs)
        if key_padding_mask is None: key_padding_mask = [None] * len(self.enc_chs)
              
        t_emb = self.t_emb(t)
                
        x = self.conv_in(x)            
        x = self.pos_enc(x) 
        
        enc_ftrs = self.encoder(x, t_emb=t_emb, c_emb=c_emb, attn_mask=attn_mask, key_padding_mask=key_padding_mask)[::-1]
        out      = self.decoder(x=enc_ftrs[0], encoder_features=enc_ftrs[1:], t_emb=t_emb, c_emb=c_emb, 
                                attn_mask=attn_mask[::-1][1:], key_padding_mask=key_padding_mask[::-1][1:])
        out      = self.head(out)       
        return out

# %% ../../src/models/unet_qc.ipynb 12
@dataclass
class QC_Compilation_UNet_config(QC_Cond_UNet_config):  
    unitary_encoder_config: Unitary_encoder_config

# %% ../../src/models/unet_qc.ipynb 13
class QC_Compilation_UNet(QC_Cond_UNet):
    """Extension of the `QC_Cond_UNet` to accept unitary conditions."""
    
    def __init__(self, model_features=[32,32,64], clr_dim=8, num_clrs=8, t_emb_size=128, cond_emb_size=512, 
                 num_heads=[8,8,2], num_res_blocks=[2, 2, 4], transformer_depths=[1,2,1], unitary_encoder_config=None): 
        
        super().__init__(model_features, clr_dim, num_clrs, t_emb_size, cond_emb_size, num_heads, num_res_blocks, transformer_depths)

        if is_dataclass(unitary_encoder_config):
            unitary_encoder_config = asdict(unitary_encoder_config)
        self.unitary_encoder = Unitary_encoder(**unitary_encoder_config)
        self.params_config   = QC_Compilation_UNet_config(model_features, self.clr_dim, self.num_clrs, self.t_emb_size, self.cond_emb_size, num_heads, num_res_blocks, transformer_depths, self.unitary_encoder.params_config)
    
    def forward(self, x, t, c_emb, U, attn_mask=None, key_padding_mask=None, **kwargs):
        u_emb = self.unitary_encoder(U)            # [batch, seq2, ch]     
        c_emb = torch.cat([c_emb, u_emb], dim=1)   # [batch, seq1+seq2, ch]  
        out = super().forward(x, t, c_emb, attn_mask, key_padding_mask, **kwargs)
        return out
