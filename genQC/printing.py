# AUTOGENERATED! DO NOT EDIT! File to edit: ../src/printing.ipynb.

# %% auto 0
__all__ = ['display_colums', 'ndarray_to_latex', 'tensor_to_latex', 'print_markdown', 'print_table']

# %% ../src/printing.ipynb 3
from .imports import *
from ipywidgets import widgets
if IN_NOTEBOOK: from IPython.display import Markdown

# %% ../src/printing.ipynb 4
def display_colums(display_list, num_col=3):
    
    outputs = [widgets.Output() for i in range(num_col)]

    for i in range(len(display_list)//num_col+1):
        
        ds = display_list[i*num_col:(i+1)*num_col]
   
        for d,output in zip(ds,outputs):
            with output:
                display(d)
             
    columns = widgets.HBox(outputs)
    display(columns)  

# %% ../src/printing.ipynb 8
def ndarray_to_latex(arr):
    """Returns a LaTeX `{pmatrix*}[r]` as a string"""
    if len(arr.shape) > 2: raise ValueError('pmatrix can at most display two dimensions')
    lines = str(arr).replace('[', '').replace(']', '').splitlines()
    rv = [r'\begin{pmatrix*}[r]']
    rv += ['  ' + ' & '.join(l.split()) + r'\\' for l in lines]
    rv +=  [r'\end{pmatrix*}']
    return '\n'.join(rv)

# %% ../src/printing.ipynb 9
def tensor_to_latex(tensor):
    """Returns a `LaTeX {pmatrix*}[r]` as a string """
    if len(tensor.shape) > 2: raise ValueError('pmatrix can at most display two dimensions')
    lines = str(tensor.numpy()).replace('[', '').replace(']', '').splitlines()
    rv = [r'\begin{pmatrix*}[r]']
    rv += ['  ' + ' & '.join(l.split()) + r'\\' for l in lines]
    rv +=  [r'\end{pmatrix*}']
    return '\n'.join(rv)

# %% ../src/printing.ipynb 11
def print_markdown(text, print_raw=False):
    if IN_NOTEBOOK and not print_raw: display(Markdown(text))
    else: print(text)

# %% ../src/printing.ipynb 14
def print_table(col_headings: list, data: np.array, row_headings=None, print_raw=False):   
    assert len(col_headings) == data.shape[1]
    if row_headings is not None: assert len(row_headings) == data.shape[0]
        
    #--------------------------------
    head = ""
    if row_headings is not None: head = "| " + head  
    
    for col_heading in col_headings: head += f"|{col_heading}"
    head += "|\n"
                
    #--------------------------------
    seperator = ""
    if row_headings is not None: seperator = "|--"
        
    for col_heading in col_headings: seperator += "|--"
    seperator += "|\n"
    
    #--------------------------------    
    body = ""
    for i, row in enumerate(data):
        body_row = ""
        for x in row:
            body_row += f"|{x:.2f}"
            
        if row_headings is not None: 
            body_row = f"|{row_headings[i]}" + body_row
        
        body += body_row + "|\n"
                
    #--------------------------------    
    table = head + seperator + body
      
    print_markdown(table, print_raw)
