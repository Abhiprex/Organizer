import sys,os,tempfile,time,json,random,re,subprocess,shutil
sys.path.insert(0,"/home/claude/repo/Organizer/src")
import app_backend as ab, organizer
from pathlib import Path
R=[]
def T(grp,name,fn):
    try: ok,note=fn()
    except Exception as e: ok,note=False,f"{type(e).__name__}: {e}"[:100]
    R.append((grp,name,ok,str(note)[:100]))
    if not ok: print("FAIL",grp,name[:55],"|",str(note)[:90],flush=True)
def B(): return ab.Backend(tempfile.mkdtemp())
def folder(files,age=1):
    p=Path(tempfile.mkdtemp())
    for f,c in files.items():
        fp=p/f; fp.parent.mkdir(parents=True,exist_ok=True); fp.write_text(c); t=time.time()-age*86400; os.utime(fp,(t,t))
    return p
def allf(p): return sorted(str(x.relative_to(p)).replace("\\","/") for x in p.rglob("*") if x.is_file())
TYPES=["report.pdf","photo.jpg","clip.mp4","song.mp3","main.c","pack.zip","setup.exe","data.csv","notes.txt","slides.pptx","fw.hex","page.html","shot.png","unknown.qqq"]
# A: preset x file type matrix (7 x 14 = 98)
for key in ["standard","by_year","student","office","photographer","embedded","minimal"]:
    for f in TYPES:
        def t(key=key,f=f):
            b=B(); b.apply_preset(key); p=folder({f:"x"}); r=b.run(p,dry_run=True,include_new=True); planned=len(r["plan"])==1
            r=b.run(p,dry_run=False,include_new=True); moved=not (p/f).exists() and r["stats"].get("errors")==0
            b.undo(p); back=(p/f).exists() and allf(p)==[f]
            return planned and moved and back,(planned,moved,back)
        T("A-preset matrix",f"{key} / {f}",t)
# B: rule editor round trips (20)
rnd=random.Random(4)
for i in range(10):
    def t(i=i):
        b=B(); ext=rnd.choice(["pdf","docx","xyz","abc","log"]); pat=rnd.choice(["inv*","*final*","a?.*","report*"]); dest=rnd.choice(["Money","Work/Docs","A B/C","Ünï/çode"])
        rule={"name":f"r{i}","extensions":[ext],"patterns":[pat],"dest":dest,"subfolders":rnd.choice([[],["year"],["extension"],["year-month"]])}
        b.add_rule(rule); row=b.rule_rows()[0]; r=b.get_rule(0)
        name=pat.replace("*","x").replace("?","1")+"."+ext; p=folder({name:"1"}); b.run(p,dry_run=False,include_new=True); got=allf(p)[0]
        return row["name"]==f"r{i}" and r["dest"]==dest and got.startswith(dest),(got,dest)
    T("B-rule round trip",f"valid rule {i}",t)
BAD=[{"name":"x","extensions":["pdf"],"dest":"../up"},{"name":"x","extensions":["pdf"],"dest":"C:\\x"},{"name":"x","extensions":["pdf"],"dest":"/root"},{"name":"x","extensions":["pdf"],"dest":"~/x"},{"name":" ","extensions":["pdf"],"dest":"x"},{"name":"x","dest":"x"},{"name":"x","regex":"(a*)*b","dest":"x"},{"name":"x","regex":"[","dest":"x"},{"name":"x","extensions":["pdf"],"dest":"x","subfolders":["nope"]},{"name":"x","extensions":["pdf"],"dest":"a/../../b"}]
for i,rule in enumerate(BAD):
    def t(rule=rule):
        b=B(); before=b.config_path.read_bytes()
        try: b.add_rule(rule); return False,"accepted"
        except ab.BackendError: return b.config_path.read_bytes()==before,"config untouched"
    T("B-rule round trip",f"invalid rule {i} rejected, settings untouched",t)
# C: pause text (10)
for text,valid in [("30m",True),("1h",True),("2h",True),("1d",True),("forever",True),("5m",True),("abc",False),("",False),("-5",False),("1x",False)]:
    def t(text=text,valid=valid):
        b=B()
        try: b.snooze(text); ok=valid and b.pause_status() is not None; b.resume(); return ok,b.pause_status()
        except ab.BackendError: return not valid,"rejected"
    T("C-pause",f"pause '{text}'",t)
# D: 20 runs then undo in random order (10 variants)
for seed in range(10):
    def t(seed=seed):
        rr=random.Random(seed); b=B(); p=folder({}); names=[]
        for i in range(12):
            n=f"f{seed}_{i}.{rr.choice(['pdf','jpg','txt','zip'])}"; names.append(n); (p/n).write_text(str(i)); t0=time.time()-86400; os.utime(p/n,(t0,t0)); b.run(p,dry_run=False,include_new=True)
        runs=[h["run"] for h in b.history(p)]; rr.shuffle(runs)
        for run in runs: b.undo(p,run)
        return sorted(allf(p))==sorted(names) and len(b.history(p))==0,(len(allf(p)),len(b.history(p)))
    T("D-history",f"12 runs undone in random order (seed {seed})",t)
# E: separate processes, separate users (5)
CODE='''
import sys,os,time,tempfile
sys.path.insert(0,"/home/claude/repo/Organizer/src")
import app_backend as ab
from pathlib import Path
b=ab.Backend(os.environ["ORGANIZER_HOME"]); p=Path(sys.argv[1]); b.apply_preset(sys.argv[2])
for i in range(30): (p/f"f{i}.pdf").write_text(str(i)); t=time.time()-86400; os.utime(p/f"f{i}.pdf",(t,t))
r=b.run(p,dry_run=False,include_new=True); h=b.history(p)
print(r["stats"]["moved"],sum(x["count"] for x in h))
'''
open("/tmp/b4_user.py","w").write(CODE)
for n in (2,3,4,6,8):
    def t(n=n):
        procs=[]; homes=[]; dirs=[]
        for i in range(n):
            home=tempfile.mkdtemp(); d=Path(tempfile.mkdtemp()); homes.append(home); dirs.append(d)
            procs.append(subprocess.Popen([sys.executable,"/tmp/b4_user.py",str(d),["standard","office","student","photographer"][i%4]],env={**os.environ,"ORGANIZER_HOME":home},stdout=subprocess.PIPE,stderr=subprocess.PIPE))
        outs=[p.communicate(timeout=120) for p in procs]
        ok=all(o[0].decode().split()==["30","30"] for o in outs) and all(len(allf(d))==30 for d in dirs)
        return ok,[o[0].decode().strip() or o[1].decode()[-60:] for o in outs][:2]
    T("E-users in parallel",f"{n} users at once, each with own history",t)
# F: where_would_go over 40 names (40)
b=B(); NAMES=["a.pdf","A.PDF","my file.docx","photo.JPG","holiday 2024.jpeg","x.mp4","y.MKV","z.mp3","code.py","main.c","page.html","style.css","a.zip","b.7z","c.rar","setup.exe","inst.msi","data.csv","sheet.xlsx","slides.pptx","notes.txt","read.md","fw.hex","dump.bin","a.elf","a.map","raw.cr2","pic.nef","clip.m4v","tune.opus","script.go","lib.rs","q.sql","icon.svg","archive.tar.gz","thing.xyz","noext","日本語.pdf","emoji😀.png","Makefile"]
before=set(os.listdir("."))
for n in NAMES:
    def t(n=n):
        dest,label=b.where_would_go(n); return dest is not None and "/" in dest or dest in ("Makefile",) or dest is not None,(dest,label)
    T("F-where would it go",n,t)
T("F-where would it go","no stray files were created",lambda:(set(os.listdir("."))==before,""))
from collections import Counter
print("TOTAL",sum(1 for r in R if r[2]),"/",len(R),dict(Counter(r[0] for r in R)))
json.dump(R,open("/tmp/results_b4.json","w"))
