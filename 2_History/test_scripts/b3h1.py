exec(open("/home/claude/t/pre3.py").read()); D="/tmp/T8/"; shutil.rmtree(D,ignore_errors=True); os.makedirs(D); os.chmod(D,0o777)
POOL=["abcdefghijklmnopqrstuvwxyz","日本語中文","éüñçø","😀🎉","ملفكتاب","0123456789"," -_()[]&+="]; EXT=["pdf","jpg","txt","zip","mp3","c","xyz","docx","PNG","Mp4","",""]
def chaos(seed):
    rnd=random.Random(seed); p=D+f"chaos{seed}"; shutil.rmtree(p,ignore_errors=True); os.makedirs(p); os.chmod(p,0o777); orig=set(); rec_=seed%2==1
    for i in range(rnd.randint(200,600)):
        stem="".join(rnd.choice(rnd.choice(POOL)) for _ in range(rnd.randint(1,40))).strip() or "x"; e=rnd.choice(EXT); n=stem+("."+e if e else ""); d=""
        if rec_ and rnd.random()<0.5: d=rnd.choice(["d1","d1/d2","d3","d4/d5/d6"])+"/"
        rel=d+n
        if rel in orig: continue
        fp=p+"/"+rel; os.makedirs(os.path.dirname(fp),exist_ok=True); open(fp,"w").write(str(rnd.randint(0,40)))
        t=time.time()-rnd.randint(0,2000)*86400; os.utime(fp,(t,t)); orig.add(rel)
    args=("-r",) if rec_ else (); rc,o=org(p,*args,to=90); rc2,o2=org(p,*args,to=90); a=cnt(p)
    rcu,ou=org(p,"--undo"); back={os.path.relpath(os.path.join(d,f),p) for d,_,fs in os.walk(p) for f in fs}
    bad=[]
    if rc!=0 or "Traceback" in o+o2+ou: bad.append("rc/traceback")
    if not errs0(o): bad.append("errors:"+(re.search(r"(\d+) errors",o) or [0,"?"])[1] if re.search(r"(\d+) errors",o) else "errors?")
    if a!=len(orig): bad.append(f"count {len(orig)}->{a}")
    if not re.search(r"\b0 moved",o2): bad.append("2nd run moved")
    if back!=orig: bad.append(f"undo mismatch missing={len(orig-back)} extra={len(back-orig)}")
    return (not bad),(", ".join(bad) or f"{len(orig)} files {'-r' if rec_ else ''}")
for s in range(1,26): TT("H",f"chaos run seed {s} (mixed names/types/dates): organize, 2nd run, undo exact",lambda s=s:chaos(s))
def kill(delay,sig,mode):
    p=D+f"k{delay}{sig}{mode}"; mk(p,{f"k{i}.pdf":str(i%97) for i in range(3000)}); pr=subprocess.Popen(["python3","organizer.py","-s",p,"-y","--min-age","0"],cwd=PK,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=ENV); time.sleep(delay); pr.send_signal(sig); pr.wait()
    moved=3000-len([f for f in os.listdir(p) if f.endswith(".pdf")])
    if mode=="undo": org(p,"--undo"); ok=len([f for f in os.listdir(p) if f.endswith(".pdf")])==3000 and cnt(p)==3000; return ok,f"killed after {moved} moved"
    rc,o=org(p); loose=len([f for f in os.listdir(p) if f.endswith(".pdf")]); return (loose==0 and cnt(p)==3000),f"killed after {moved} moved; rerun loose={loose}"
for k,d in enumerate([0.12,0.2,0.3,0.4,0.5,0.6,0.7,0.8,0.9,1.0]): TT("H",f"SIGKILL at {d}s, then undo restores all 3000",lambda d=d:kill(d,9,"undo"))
for d in [0.15,0.25,0.35,0.45,0.55]: TT("H",f"SIGTERM at {d}s, then undo restores all 3000",lambda d=d:kill(d,15,"undo"))
for d in [0.15,0.3,0.45,0.6,0.75]: TT("H",f"SIGKILL at {d}s, immediate re-run finishes the job",lambda d=d:kill(d,9,"rerun"))
save("b3h1")
