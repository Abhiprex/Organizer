exec(open("/home/claude/t/pre3.py").read()); D="/tmp/T7/"; shutil.rmtree(D,ignore_errors=True); os.makedirs(D); os.chmod(D,0o777)
OLD=1709600000
# A: 7 subfolder options x 5 categories (35)
for opt,chk in [("extension",None),("year","2024"),("month",None),("year-month","2024-03"),("first-letter","S"),("size",None),("topic",None)]:
    for fn,top in [("sample.mp4","Videos"),("sample.mp3","Audio"),("sample.py","Code"),("sample.zip","Archives"),("sample.docx","Documents")]:
        def f(opt=opt,chk=chk,fn=fn,top=top):
            p=D+f"a_{opt}_{fn}"; mk(p,{fn:"x"}); os.utime(p+"/"+fn,(OLD,OLD)); rc,o=org(p,"--subfolders",opt); r=find(p,fn)
            return (rc==0 and r is not None and r.startswith(top) and errs0(o) and (chk is None or chk in r)),r
        TT("M",f"--subfolders {opt} on {fn}",f)
# B: conflict modes x 6 categories (18)
def cm(mode,ext,top):
    def f():
        p=D+f"b_{mode}_{ext}"; mk(p,{f"a.{ext}":"new"}); rc,o=org(p); 
        mk(p+"_x",{}); shutil.rmtree(p+"_x")
        dest=os.path.dirname(find(p,f"a.{ext}")); fp=p+"/"+dest+f"/a.{ext}"
        open(p+f"/a.{ext}","w").write("NEWER"); org(p,"--on-conflict",mode)
        fs=allf(p); conts=[open(p+"/"+x,"rb").read() for x in fs]
        if mode=="rename": ok=b"new" in conts and b"NEWER" in conts
        elif mode=="skip": ok=os.path.exists(p+f"/a.{ext}") and open(fp).read()=="new"
        else: ok=open(fp).read()=="NEWER" and (b"new" in conts or any(b"new"==open(x,"rb").read() for x in glob.glob(PK+"/history/**/*",recursive=True) if os.path.isfile(x)))
        return ok,fs[:3]
    return f
for mode in ("rename","skip","overwrite"):
    for ext,top in [("pdf","Documents"),("jpg","Images"),("mp3","Audio"),("c","Code"),("zip","Archives"),("exe","Installers")]: TT("M",f"conflict {mode} on .{ext}",cm(mode,ext,top))
# C: folder organizing (19)
def fold(name,files,expect,age=3):
    def f():
        p=D+f"c_{abs(hash(name+str(files)))}"; mk(p,{f"{name}/{k}":v for k,v in files.items()},age_days=age); ago(p+"/"+name,age); org(p)
        r=[x for x in allf(p) if x.endswith("/"+list(files)[0])]; r=r[0] if r else None
        return (r is not None and (r.startswith(expect+"/"+name) if expect else r==f"{name}/{list(files)[0]}")),r
    return f
TT("M","folder: 3 photos -> Folders/Photos",fold("trip",{"a.jpg":"1","b.jpg":"2","c.png":"3"},"Folders/Photos"))
TT("M","folder: 2 videos -> Folders/Videos",fold("clips",{"a.mp4":"1","b.mkv":"2"},"Folders/Videos"))
TT("M","folder: 3 audio -> Folders/Audio",fold("music",{"a.mp3":"1","b.wav":"2","c.flac":"3"},"Folders/Audio"))
TT("M","folder: 2 documents -> Folders/Documents",fold("papers",{"a.pdf":"1","b.docx":"2"},"Folders/Documents"))
TT("M","folder: 2 code files -> Folders/Code",fold("snips",{"a.py":"1","b.c":"2"},"Folders/Code"))
for mk_,ex in [(".git/config","x"),("package.json","{}"),("pyproject.toml","x"),("platformio.ini","x"),("CMakeLists.txt","x"),("Makefile","x"),("board.ioc","x"),("proj.uvprojx","x"),("app.sln","x"),("blink.ino","x")]:
    TT("M",f"folder with {mk_.split('/')[0]} -> Folders/Projects",fold("proj",{mk_:ex,"notes.txt":"n"},"Folders/Projects"))
TT("M","folder: only 2 photos stays loose (needs 3)",fold("few",{"a.jpg":"1","b.jpg":"2"},None))
TT("M","folder: 3 photos but only 5 hours old stays",fold("fresh",{"a.jpg":"1","b.jpg":"2","c.jpg":"3"},None,age=0.2))
TT("M","folder: mixed types, no majority stays loose",fold("mix",{"a.jpg":"1","b.mp3":"2","c.pdf":"3"},None))
# D: topics (9)
def top(name,expect):
    def f():
        p=D+f"d_{abs(hash(name))}"; mk(p,{name:"x"}); org(p); r=find(p,name); return (("RTOS" in r) if False else None)  if False else (None,None)
    return f
def topic(name,topicname,should):
    def f():
        p=D+f"d_{abs(hash(name))}"; mk(p,{name:"x"}); org(p); r=find(p,name); return ((topicname in (r or ""))==should and r is not None),r
    return f
for t in ["RTOS","IoT","ARM","RISC-V","Microcontrollers","Resume"]: TT("M",f"topic {t} matches '{t}_notes.pdf'",topic(f"{t}_notes.pdf",t,True))
TT("M","topic ARM does NOT match 'ARMOR_notes.pdf'",topic("ARMOR_notes.pdf","ARM",False))
TT("M","topic RTOS does NOT match 'RTOSX.pdf'",topic("RTOSX.pdf","RTOS",False))
TT("M","topic matches lowercase 'rtos notes.pdf'",topic("rtos notes.pdf","RTOS",True))
# E: built-in ignores (10)
for n in ["desktop.ini","Thumbs.db",".DS_Store","shortcut.lnk","my password list.csv",".hidden.pdf","dl.pdf.crdownload","dl.pdf.part","dl.tmp","dl.pdf.download"]:
    def f(n=n):
        p=D+f"e_{abs(hash(n))}"; mk(p,{n:"x","ok.pdf":"y"}); org(p); return os.path.exists(p+"/"+n) and not os.path.exists(p+"/ok.pdf"),allf(p)
    TT("M",f"{n} left alone",f)
# F: recursive (5) + clean-empty (4)
for k,files in enumerate([{"sub/a.pdf":"1","b.pdf":"2"},{"s1/s2/s3/a.jpg":"1"},{"x/a.pdf":"1","y/a.pdf":"2"},{"keep/package.json":"{}","keep/a.pdf":"1","z/b.pdf":"2"},{"a/b/c/d/e.mp3":"1","f.mp3":"2"}]):
    def f(files=files,k=k):
        p=D+f"f{k}"; mk(p,files); b=cnt(p); rc,o=org(p,"-r"); rc2,o2=org(p,"-r"); return (rc==0 and errs0(o) and cnt(p)==b and re.search(r"\b0 moved",o2) is not None),f"{b}->{cnt(p)}"
    TT("M",f"recursive layout {k+1}: no loss, 0 errors, 2nd run idle",f)
for k in range(4):
    def f(k=k):
        p=D+f"g{k}"; mk(p,{"a.pdf":"1","b.jpg":"2","c.mp3":"3"}); org(p); org(p,"--undo"); org(p,"--clean-empty"); left=[d for d in os.listdir(p) if os.path.isdir(p+"/"+d)]
        return (len(left)==0 and cnt(p)==3),left
    TT("M",f"undo then --clean-empty leaves no empty folders (#{k+1})",f)
save("b3m")
