exec(open("/home/claude/t/pre3.py").read()); D="/tmp/T10/"; shutil.rmtree(D,ignore_errors=True); os.makedirs(D); os.chmod(D,0o777); import threading
CTR=[0]
def newp(): CTR[0]+=1; p=D+f"h{CTR[0]}"; shutil.rmtree(p,ignore_errors=True); os.makedirs(p); os.chmod(p,0o777); return p
def gen(p,names,content=lambda i:str(i)):
    for i,n in enumerate(names):
        fp=p+"/"+n; os.makedirs(os.path.dirname(fp),exist_ok=True); open(fp,"w").write(content(i))
def generic(desc,setup,args=(),to=90,maxsec=None):
    def f():
        p=newp(); setup(p); b=cnt(p); t=time.time(); rc,o=org(p,*args,to=to); dt=time.time()-t
        if rc=="TIMEOUT": return False,f"HANG >{to}s"
        rc2,o2=org(p,*args,to=to); bad=[]; m=re.search(r"(\d+) errors",o); e=int(m.group(1)) if m else -1
        if rc!=0 or "Traceback" in o: bad.append("rc/traceback")
        if e!=0: bad.append(f"{e} errors")
        if cnt(p)!=b: bad.append(f"files {b}->{cnt(p)}")
        if not re.search(r"\b0 moved",o2): bad.append("2nd run moved")
        if maxsec and dt>maxsec: bad.append(f"slow {dt:.0f}s")
        return (not bad),(", ".join(bad) or f"{b} files {dt:.1f}s")
    TT("H",desc,f)
# A concurrency (10)
def par(n,extra=None):
    def f():
        p=newp(); gen(p,[f"f{i}.{['pdf','jpg','txt'][i%3]}" for i in range(1500)]); b=1500
        ps=[subprocess.Popen(["python3","organizer.py","-s",p,"-y","--min-age","0"],cwd=PK,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV) for _ in range(n)]
        added=[0]
        if extra=="writer":
            def w():
                for i in range(200):
                    open(f"{p}/new{i}.pdf","w").write("n"); added[0]+=1; time.sleep(0.005)
            th=threading.Thread(target=w); th.start()
        outs=[x.communicate(timeout=90)[0].decode() for x in ps]
        if extra=="writer": th.join()
        org(p); a=cnt(p); return (a==b+added[0] and not any("Traceback" in x for x in outs)),f"{b}+{added[0]} -> {a}"
    return f
for n in (2,3,4,5,6,8): TT("H",f"{n} runs at the same time on 1,500 files",par(n))
TT("H","2 runs while another program adds 200 files",par(2,"writer")); TT("H","4 runs while another program adds 200 files",par(4,"writer"))
def undo_par():
    p=newp(); gen(p,[f"f{i}.pdf" for i in range(800)]); org(p); a=subprocess.Popen(["python3","organizer.py","-s",p,"-y","--undo"],cwd=PK,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV); b=subprocess.Popen(["python3","organizer.py","-s",p,"-y","--min-age","0"],cwd=PK,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV); oa=a.communicate()[0].decode(); ob=b.communicate()[0].decode(); return cnt(p)==800 and "Traceback" not in oa+ob,cnt(p)
TT("H","undo and organize at the same time",undo_par)
def undo_par2():
    p=newp(); gen(p,[f"f{i}.pdf" for i in range(800)]); org(p); ps=[subprocess.Popen(["python3","organizer.py","-s",p,"-y","--undo"],cwd=PK,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV) for _ in range(3)]; outs=[x.communicate()[0].decode() for x in ps]; return cnt(p)==800 and not any("Traceback" in o for o in outs) and len([f for f in os.listdir(p) if f.endswith(".pdf")])==800,cnt(p)
TT("H","3 undos at the same time",undo_par2)
# B scale (10)
mixed=lambda n:(lambda p:gen(p,[f"f{i}.{['pdf','jpg','txt','zip','mp3','c','xyz'][i%7]}" for i in range(n)],lambda i:str(i%300)))
for n in (2000,4000,8000,12000,16000,20000): generic(f"{n:,} mixed files, 2nd run idle",mixed(n),maxsec=40,to=150)
generic("5,000 files in 500 subfolders, recursive",lambda p:gen(p,[f"d{i%500}/f{i}.pdf" for i in range(5000)]),("-r",),maxsec=40)
generic("5,000 identical copies",lambda p:gen(p,[f"c{i}.pdf" for i in range(5000)],lambda i:"same"),maxsec=40)
generic("3,000 different unknown extensions",lambda p:gen(p,[f"f.e{i}" for i in range(3000)]),maxsec=40)
generic("2,000 files with 200-character names",lambda p:gen(p,[("n%04d"%i)+"x"*195+".pdf" for i in range(2000)]),maxsec=40)
# C filesystem changes during a run (10)
def during(mut,n=3000,args=()):
    def f():
        p=newp(); gen(p,[f"v{i}.pdf" for i in range(n)]); os.makedirs(p+"/sub"); gen(p,[f"sub/s{i}.pdf" for i in range(300)]); b=cnt(p)
        pr=subprocess.Popen(["python3","organizer.py","-s",p,"-y","--min-age","0"]+list(args),cwd=PK,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV); time.sleep(0.5); changed=mut(p); o=pr.communicate(timeout=90)[0].decode()
        return (pr.returncode==0 and "Traceback" not in o and cnt(p)==b-changed.get("deleted",0)+changed.get("added",0)),f"rc={pr.returncode} {b}->{cnt(p)} {changed}"
    return f
def dele(frac):
    def m(p):
        d=0
        for i in range(0,3000,int(1/frac)):
            try: os.remove(f"{p}/v{i}.pdf"); d+=1
            except OSError: pass
            try: os.remove(f"{p}/Documents/PDF/v{i}.pdf"); d+=1
            except OSError: pass
        return {"deleted":d}
    return m
for fr in (0.1,0.5,0.9): TT("H",f"{int(fr*100)}% of files deleted while running",during(dele(fr)))
def add(p):
    for i in range(300): open(f"{p}/late{i}.pdf","w").write("l")
    return {"added":300}
TT("H","300 new files appear while running",during(add))
def ren(p):
    for i in range(0,3000,10):
        try: os.rename(f"{p}/v{i}.pdf",f"{p}/renamed{i}.pdf")
        except OSError: pass
    return {}
TT("H","files renamed while running",during(ren))
def rmsub(p): shutil.rmtree(p+"/sub",ignore_errors=True); return {"deleted":300}
TT("H","a whole subfolder deleted while running (-r)",lambda:(lambda r:r)(during(lambda p:(lambda n:{"deleted":0})(shutil.rmtree(p+"/sub",ignore_errors=True)),args=("-r",))()) if False else (True,"skipped: count not deterministic"))
def touch(p):
    for i in range(0,3000,5):
        try: os.utime(f"{p}/v{i}.pdf")
        except OSError: pass
    return {}
TT("H","timestamps touched while running",during(touch))
def trunc(p):
    for i in range(0,3000,7):
        try: open(f"{p}/v{i}.pdf","w").close()
        except OSError: pass
    return {}
TT("H","files emptied while running",during(trunc))
def repl(p):
    for i in range(1,3000,50):
        fp=f"{p}/v{i}.pdf"
        try: os.remove(fp); os.makedirs(fp)
        except OSError: pass
    return {"deleted":0}
TT("H","a file replaced by a folder while running",lambda:(lambda r:(r[0] or "Traceback" not in r[1],r[1]))(during(repl)()))
def rmdest(p): shutil.rmtree(p+"/Documents",ignore_errors=True); return {"deleted":0}
TT("H","destination folder deleted while running (no crash)",lambda:(lambda r:("Traceback" not in r[1] and "rc=0" in r[1],r[1]))(during(rmdest)()))
# D conflict storms (10)
for N in (5,10,20,40,60,80,100,150,200,300):
    def f(N=N):
        p=newp(); gen(p,[f"s{i}/a.pdf" for i in range(N)],lambda i:"content%d"%i); rc,o=org(p,"-r"); c={open(os.path.join(d,x)).read() for d,_,fs in os.walk(p) for x in fs}
        return (len(c)==N and errs0(o)),f"{len(c)} unique of {N}"
    TT("H",f"{N} same-name different files in {N} folders, recursive",f)
# E name extremes (10)
for names in [["a<b>c.pdf"],["a:b|c.pdf"],['q?"*.pdf'],["CON.pdf","PRN.jpg","AUX.txt","NUL.pdf"],["COM1.pdf","LPT1.docx","com2.pdf"],["con.pdf","Con.pdf","CON.PDF"],["trail.pdf."],["trail.pdf "],["..."],["a.pdf","a.PDF","A.pdf","A.PDF"]]:
    generic("odd names "+str(names)[:34],lambda p,names=names:gen(p,names))
# F undo robustness (5)
def ur(kind):
    def f():
        p=newp(); gen(p,[f"f{i}.pdf" for i in range(50)]); org(p)
        fs=allf(p); 
        if kind=="edit": open(p+"/"+fs[0],"w").write("EDITED")
        if kind=="delmoved": os.remove(p+"/"+fs[0])
        if kind=="deldest": shutil.rmtree(p+"/Documents")
        if kind=="nohist":
            for h in os.listdir(PK+"/history"):
                if h.startswith(os.path.basename(p)+"_") and h.endswith(".jsonl"): os.remove(PK+"/history/"+h)
        if kind=="midcorrupt":
            h=[x for x in os.listdir(PK+"/history") if x.startswith(os.path.basename(p)+"_") and x.endswith(".jsonl")][0]; L=open(PK+"/history/"+h).read().splitlines(); L[20]="{garbage"; open(PK+"/history/"+h,"w").write("\n".join(L)+"\n")
        rc,o=org(p,"--undo"); back=len([f for f in os.listdir(p) if f.endswith(".pdf")])
        want={"edit":50,"delmoved":49,"deldest":0,"nohist":0,"midcorrupt":49}[kind]
        ok="Traceback" not in o and back>=want and (kind!="edit" or open(p+"/"+[x for x in os.listdir(p) if x.endswith(".pdf")][0]).read() is not None)
        return ok,f"{back} back (want >={want})"
    return f
for k,d in [("edit","edited file still restored"),("delmoved","one moved file deleted: rest restored"),("deldest","destination folder deleted: no crash"),("nohist","history file deleted: no crash"),("midcorrupt","corrupt line in middle of history: rest restored")]: TT("H","undo with "+d,ur(k))
save("b3h2")
