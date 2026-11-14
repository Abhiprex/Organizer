"""A stand-in for tkinter that records what the app does, so the window code can be exercised without a screen."""
import sys, types
class Var:
    def __init__(self,master=None,value=None,**k): self.v=value if value is not None else ""
    def get(self): return self.v
    def set(self,v): self.v=v
class W:
    created=[]
    def __init__(self,*a,**k): self.a=a; self.k=k; self.cmd=k.get("command"); W.created.append(self); self.vals=list(k.get("values",[])) if "values" in k else []; self.cur=""; self.bound={}
    def __getattr__(self,name):
        if name.startswith("__"): raise AttributeError(name)
        return lambda *a,**k: None
    def bind(self,ev,fn,*a): self.bound[ev]=fn
    def configure(self,**k):
        if "values" in k: self.vals=list(k["values"])
    config=configure
    def set(self,v): self.cur=v
    def get(self,*a): return self.cur
    def after(self,ms,fn=None,*a): self.__dict__.setdefault("after_calls",[]).append((ms,fn)); return len(self.after_calls)
    def after_cancel(self,i): pass
    def wait_window(self,w): pass
class Tree(W):
    def __init__(self,*a,**k): super().__init__(*a,**k); self.rows={}; self.sel=[]; self.n=0
    def insert(self,parent,idx,values=(),iid=None,**k): self.n+=1; i=iid or f"I{self.n}"; self.rows[i]=list(values); return i
    def delete(self,*ids):
        if not ids: return
        for i in ids: self.rows.pop(i,None)
    def get_children(self,*a): return tuple(self.rows)
    def item(self,i,opt=None): return {"values":self.rows[i]}
    def selection(self): return tuple(self.sel)
class Listbox(W):
    def __init__(self,*a,**k): super().__init__(*a,**k); self.items=[]; self.sel=()
    def insert(self,pos,item): self.items.append(item)
    def delete(self,a,b=None): self.items=[]
    def curselection(self): return self.sel
    def get(self,i): return self.items[i]
class Text(W):
    def __init__(self,*a,**k): super().__init__(*a,**k); self.text=""
    def delete(self,a,b=None): self.text=""
    def insert(self,pos,s): self.text+=s
class Notebook(W):
    def __init__(self,*a,**k): super().__init__(*a,**k); self.tabs=[]; self.idx=0
    def add(self,frame,text=""): self.tabs.append(text)
    def select(self,*a): return self.idx
    def index(self,x): return self.idx
class Tk(W):
    def winfo_screenwidth(self): return 1920
    def winfo_screenheight(self): return 1080
class Style(W):
    def theme_names(self): return ("clam","default")
script={"askyesno":True,"askstring":[],"askdirectory":"","askopenfilename":"","asksaveasfilename":""}
log=[]
def install():
    tk=types.ModuleType("tkinter"); ttk=types.ModuleType("tkinter.ttk"); mb=types.ModuleType("tkinter.messagebox"); fd=types.ModuleType("tkinter.filedialog"); sd=types.ModuleType("tkinter.simpledialog")
    for n in ("StringVar","BooleanVar","IntVar"): setattr(tk,n,Var)
    tk.Tk=Tk; tk.Toplevel=W; tk.Text=Text; tk.Listbox=Listbox; tk.END="end"
    for n in ("Frame","Label","Button","Entry","Checkbutton","Combobox","Progressbar","Scrollbar","LabelFrame"): setattr(ttk,n,W)
    ttk.Treeview=Tree; ttk.Notebook=Notebook; ttk.Style=Style
    for n in ("showinfo","showwarning","showerror"): setattr(mb,n,(lambda n: lambda *a,**k: log.append((n,a[1] if len(a)>1 else a)))(n))
    mb.askyesno=lambda *a,**k: (log.append(("askyesno",a[1] if len(a)>1 else a)), script["askyesno"])[1]
    fd.askdirectory=lambda **k: script["askdirectory"]; fd.askopenfilename=lambda **k: script["askopenfilename"]; fd.asksaveasfilename=lambda **k: script["asksaveasfilename"]
    sd.askstring=lambda *a,**k: script["askstring"].pop(0) if script["askstring"] else None
    tk.ttk=ttk; tk.messagebox=mb; tk.filedialog=fd; tk.simpledialog=sd
    sys.modules.update({"tkinter":tk,"tkinter.ttk":ttk,"tkinter.messagebox":mb,"tkinter.filedialog":fd,"tkinter.simpledialog":sd})
