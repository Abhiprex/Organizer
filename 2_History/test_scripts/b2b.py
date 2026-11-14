s=open("big.py").read().split("# ---------- SIMPLE ----------")[0]
exec(s); D="/tmp/T4/"; shutil.rmtree(D,ignore_errors=True); os.makedirs(D); os.chmod(D,0o777)
R2=[]; K=[0]
def cnt(p): return sum(1 for d,ds,fs in os.walk(p) for x in fs)+sum(1 for d,ds,fs in os.walk(p) for x in ds if os.path.islink(os.path.join(d,x)))
def H(desc,setup,args=(),user=False,to=60,second=True):
    K[0]+=1; id=f"H2-{K[0]:02d}"; p=D+f"h{K[0]}"
    try:
        shutil.rmtree(p,ignore_errors=True); os.makedirs(p); os.chmod(p,0o777); setup(p); b=cnt(p); t=time.time(); rc,o=org(p,*args,user=user,to=to); dt=time.time()-t
        if rc=="TIMEOUT": ok,note=False,f"HANG >{to}s"
        else:
            a=cnt(p); m=re.search(r"(\d+) errors",o); e=int(m.group(1)) if m else -1; bad=[]
            if rc!=0: bad.append(f"rc={rc}")
            if "Traceback" in o or "Logging error" in o: bad.append("traceback/log error")
            if e!=0: bad.append(f"{e} errors")
            if a!=b: bad.append(f"files {b}->{a}")
            if second:
                rc2,o2=org(p,*args,user=user,to=to)
                if rc2!="TIMEOUT" and not re.search(r"\b0 moved",o2): bad.append("2nd run moved more")
            ok,note=(not bad),(", ".join(bad) or f"{b} files, {dt:.1f}s")
    except Exception as ex: ok,note="ERR",repr(ex)[:80]
    R2.append(("H",id,desc,ok,note))
    if ok is not True: print("H",id,"FAIL" if ok is False else ok,desc[:48],"|",note[:80],flush=True)
def files(names,content=None): 
    def s(p):
        for i,n in enumerate(names):
            fp=os.path.join(p,n); os.makedirs(os.path.dirname(fp),exist_ok=True); open(os.path.join(p,n) if not isinstance(n,bytes) else os.path.join(p.encode(),n),"w" if not isinstance(n,bytes) else "wb").write(str(i) if not isinstance(n,bytes) else b"x")
    return s
# names: lengths
for L in (1,100,200,240,251): H(f"name stem length {L}",files(["x"*L+".pdf"]))
H("multibyte 244 bytes (日 x80)",files(["日"*80+".pdf"])); H("multibyte 253 bytes (日 x83)",files(["日"*83+".pdf"])); H("emoji 244 bytes",files(["😀"*60+".pdf"]))
for n in ["ملف.pdf","फ़ाइल.pdf","файл.pdf","📄doc.pdf","e\u0301.pdf"]: H("script name "+repr(n)[:12],files([n]))
for n in ["a  b.pdf"," lead.pdf","trail .pdf","a'b\".pdf","a&b;c|d.pdf","50%.pdf","[x](y).pdf","{a}$HOME#b.pdf","a\tb.pdf","a\nb.pdf"]: H("special chars "+repr(n)[:14],files([n]))
# counts / sizes
H("1,000 files",files([f"f{i}.pdf" for i in range(1000)]))
H("5,000 pdf files",files([f"f{i}.pdf" for i in range(5000)]))
H("10,000 mixed files",files([f"f{i}.{['pdf','jpg','txt','zip','mp3','c','xyz'][i%7]}" for i in range(10000)]),to=120)
def sparse(n,mb): 
    def s(p):
        for i in range(n): f=open(f"{p}/big{i}.pdf","wb"); f.truncate(mb*1024*1024); f.close()
    return s
H("one 1 GB sparse file",sparse(1,1024)); H("five 512 MB sparse files (same content)",sparse(5,512))
H("3,000 files in one subfolder, recursive",files([f"sub/f{i}.pdf" for i in range(3000)]),("-r",))
def deep(n):
    def s(p):
        d=p
        for i in range(n): d+="/d"
        os.makedirs(d); open(d+"/a.pdf","w").write("1")
    return s
H("50 nested levels, recursive",deep(50),("-r",)); H("200 nested levels, recursive",deep(200),("-r",))
H("500 empty subfolders, recursive",lambda p:[os.makedirs(f"{p}/e{i}") for i in range(500)],("-r",))
H("1,000 different unknown extensions",files([f"f.ext{i}" for i in range(1000)]))
# dates
def dated(ts):
    def s(p):
        open(p+"/a.pdf","w").write("1")
        try: os.utime(p+"/a.pdf",(ts,ts))
        except Exception: pass
    return s
for name,ts in [("1970-01-02",86400),("epoch 0",0),("1901 (negative)",-2000000000),("year 2100",4102444800),("year 2262",9223372036),("tomorrow",time.time()+86400)]: H("mtime "+name,dated(ts))
# conflicts
H("20 same-name different files in 20 subfolders, recursive",lambda p:[(os.makedirs(f"{p}/s{i}"),open(f"{p}/s{i}/a.pdf","w").write(str(i))) for i in range(20)],("-r",))
H("100 identical copies",files([f"c{i}.pdf" for i in range(100)]) if False else (lambda p:[open(f"{p}/c{i}.pdf","w").write("same") for i in range(100)]))
def pre(extra):
    def s(p):
        os.makedirs(p+"/Documents/PDF"); 
        for n in extra: open(f"{p}/Documents/PDF/{n}","w").write("old"+n)
        open(p+"/a.pdf","w").write("new")
    return s
H("clash and 'a (1).pdf' already exists",pre(["a.pdf","a (1).pdf"])); H("clash with (1)..(5) all taken",pre(["a.pdf"]+[f"a ({i}).pdf" for i in range(1,6)]))
H("name that already ends in (1)",lambda p:(os.makedirs(p+"/Documents/PDF"),open(p+"/Documents/PDF/a (1).pdf","w").write("o"),open(p+"/a (1).pdf","w").write("n")))
H("A.PDF vs a.pdf in destination",lambda p:(os.makedirs(p+"/Documents/PDF"),open(p+"/Documents/PDF/A.pdf","w").write("o"),open(p+"/a.pdf","w").write("n")))
# special files / permissions
def ro(p): open(p+"/a.pdf","w").write("1"); os.chmod(p+"/a.pdf",0o444)
H("read-only (444) file",ro,user=True)
def locked(p): os.makedirs(p+"/sub"); open(p+"/sub/a.pdf","w").write("1"); open(p+"/b.pdf","w").write("2"); os.chmod(p+"/sub",0o555)
H("file inside unwritable subfolder, recursive",locked,("-r",),user=True)
def hl(p): open(p+"/a.pdf","w").write("1"); os.link(p+"/a.pdf",p+"/b.pdf")
H("two hard links to one file",hl)
def sl(p): open(p+"/a.pdf","w").write("1"); os.symlink(p+"/a.pdf",p+"/link.pdf")
H("symlink to a file in same folder",sl)
H("named pipe (FIFO) called x.pdf",lambda p:(os.mkfifo(p+"/x.pdf"),open(p+"/a.pdf","w").write("1")),to=20)
H("directory named like a file (x.pdf/)",lambda p:(os.makedirs(p+"/x.pdf"),open(p+"/x.pdf/in.txt","w").write("1"),open(p+"/a.pdf","w").write("1")))
H("destination folder path is 200 chars long",lambda p:(os.makedirs(p+"/Documents"),open(p+"/a.pdf","w").write("1")) )
def weird_src(p): pass
json.dump(R2,open("/tmp/results_b2b.json","w"))
# last test needs a weird source path
K[0]+=1; wp=D+"sp "+"é"*60+" folder"; shutil.rmtree(wp,ignore_errors=True); os.makedirs(wp); open(wp+"/a.pdf","w").write("1"); rc,o=org(wp)
ok=(rc==0 and " 0 errors" in o and not os.path.exists(wp+"/a.pdf")); R2.append(("H",f"H2-{K[0]:02d}","source path with spaces + 60 accents",ok,"")); 
if not ok: print("H","source path weird FAIL",o[-80:])
json.dump(R2,open("/tmp/results_b2b.json","w"))
print("TOTAL H",sum(1 for r in R2 if r[3] is True),"/",len(R2))
