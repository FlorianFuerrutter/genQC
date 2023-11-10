# AUTOGENERATED! DO NOT EDIT! File to edit: ../../src/dataset/config_dataset.ipynb.

# %% auto 0
__all__ = ['Config_Dataset_config', 'Config_Dataset']

# %% ../../src/dataset/config_dataset.ipynb 2
from ..imports import *
from ..config_loader import *

# %% ../../src/dataset/config_dataset.ipynb 3
@dataclass
class Config_Dataset_config:
    """Config `dataclass` used for storage."""
    store_dict: dict 

# %% ../../src/dataset/config_dataset.ipynb 4
class Config_Dataset():  
    """Base class for datasets, manages loading and saving."""
    
    req_params = [f.name for f in dataclasses.fields(Config_Dataset_config)]
    comment    = ""
    
    def __init__(self, device: torch.device=torch.device("cpu"), **parameters):
        req_params = self.req_params      
        for p in req_params:
            if p not in parameters: raise RuntimeError(f"Missing parameter `{p}` in argument `**parameters: dict`")           

        self.device = device      #parameters will overwrite passed device
        
        for k,v in parameters["store_dict"].items(): 
            if   v == "tensor"     : setattr(self, str(k), torch.tensor([0], device=self.device))
            elif v == "tensor_list": setattr(self, str(k), [torch.tensor([0], device=self.device)]) 
            elif v == "list"       : setattr(self, str(k), ["list str entry"]) 
            elif v == "numpy"      : setattr(self, str(k), np.array(["numpy str entry"]))                                             
            else                   : raise RuntimeError(f"Unknown type `{v}` in argument parameters[`store_dict`]")
                                             
        for k,v in parameters.items(): setattr(self, str(k), v)
           
    def to(self, device: torch.device, excepts=[], **kwargs):
        self.device = device
        
        for k,v in self.store_dict.items(): 
            if k in excepts: continue
            
            if v == "tensor": 
                x = getattr(self, str(k)).to(device, **kwargs)
                setattr(self, str(k), x)
                
            elif v == "tensor_list": 
                x = getattr(self, str(k))
                x = [ix.to(device, **kwargs) for ix in x]
                setattr(self, str(k), x)
  
        return self
    
    #----------------------------
    
    @property
    def params_config(self):
        params_config = {}              
        for p in self.req_params: params_config[p] = getattr(self, p)
        return params_config   
       
    def get_config(self, save_path=None, without_metadata=False):
        if not without_metadata:       
            config = {}
            config["target"]         = class_to_str(type(self))
            config["device"]         = str(self.device)
            config["comment"]        = self.comment
            config["save_path"]      = self.save_path if hasattr(self, "save_path") else save_path
            config["save_datetime"]  = datetime.now().strftime("%m/%d/%Y %H:%M:%S")
            config["params"]         = self.params_config  
        else:
            config = self.params_config  
        
        self.config = config        
        return config
            
    def save_dataset(self, config_path: str, save_path: str):
        config = self.get_config(save_path, without_metadata=False)
        save_dict_yaml(config, config_path)                                   
        self.store_x_y(save_path)          
   
    #----------------------------
    
    def store_x_y(self, path_str):       
        for k,v in self.store_dict.items(): 
            x = getattr(self, str(k))
            torch.save(x, path_str + f"_{k}.pt")
                
    def load_x_y(self, path_str):
        self.save_path = path_str
        
        for k,v in self.store_dict.items(): 
            x = torch.load(path_str + f"_{k}.pt")
            setattr(self, str(k), x)
        
    #----------------------------
    
    @staticmethod
    def from_config(config, device: torch.device, save_path: str=None):
        """Use this if we have a loaded config."""
        
        config_Dataset = instantiate_from_config(config)
        
        if "comment" in config: config_Dataset.comment = config["comment"]
        
        #--------------------------------        
        if not exists(save_path):            
            if "save_path" in config: save_path = config["save_path"]
            else:                     print("[INFO]: Found no key `save_path` path in config.")
                                  
        if exists(save_path): config_Dataset.load_x_y(save_path)
        else:                 print("[INFO]: No save_path` provided. Nothing loaded.")

        #--------------------------------
        
        config_Dataset = config_Dataset.to(device)
        print(f"[INFO]: Instantiated config_Dataset from given config on {device}.")
        
        return config_Dataset
    
    @staticmethod
    def from_config_file(config_path, device: torch.device, save_path: str=None):
        config = load_config(config_path)
        return Config_Dataset.from_config(config, device, save_path)
