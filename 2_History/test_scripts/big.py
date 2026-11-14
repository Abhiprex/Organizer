import os,subprocess,shutil,json,time,re,unicodedata,signal,glob,sys
PK=os.environ.get("PK","/tmp/nb3"); ENV={**os.environ,"HOME":"/tmp/nbhome"}; R=[]
def org(folder,*a,cfg=None,user=False,to=60,age0=True):
    cmd=["python3","organizer.py"]+(["-s",folder] if folder else [])+["-y"]+(["--min-age","0"] if age0 else [])+list(a)+(["-c",cfg] if cfg else [])
    pre=(lambda:(os.setgid(65534),os.setuid(65534))) if user else None
    try:
        r=subprocess.run(cmd,cwd=PK,capture_output=True,timeout=to,env=ENV,preexec_fn=pre); return r.returncode,(r.stdout+r.stderr).decode("utf8","replace")
    except subprocess.TimeoutExpired: return "TIMEOUT",""
def mk(p,files=None,age_days=None):
    shutil.rmtree(p,ignore_errors=True);os.makedirs(p);os.chmod(p,0o777)
    for f,c in (files or {}).items():
        fp=os.path.join(p,f);os.makedirs(os.path.dirname(fp),exist_ok=True)
        open(fp,"wb").write(c if isinstance(c,bytes) else c.encode())
        if age_days: t=time.time()-age_days*86400; os.utime(fp,(t,t))
def allf(p): return sorted(os.path.relpath(os.path.join(d,f),p) for d,_,fs in os.walk(p) for f in fs)
def find(p,name): 
    for f in allf(p):
        if os.path.basename(f)==name: return f
def cfgwith(**kw):
    c=json.load(open(PK+"/organizer_config.json")); c.update(kw); n=f"/tmp/T/c{len(os.listdir('/tmp/T'))}{time.time_ns()}.json"; json.dump(c,open(n,"w")); return n
def T(pri,id,desc,fn):
    try: ok,note=fn()
    except Exception as e: ok,note="ERR",repr(e)[:100]
    R.append((pri,id,desc,ok,note)); print(pri,id,"PASS" if ok is True else ("FAIL" if ok is False else str(ok)),desc[:50],"|",str(note)[:70],flush=True)
D="/tmp/T/"
# ---------- SIMPLE ----------
S=D+"S"; mk(S,{"report.pdf":"1","photo.jpg":"2","movie.mp4":"3","song.mp3":"4","main.c":"5","archive.zip":"6","setup.exe":"7","Screenshot 2026-01-01 at 10.00.00.png":"8","RTOS_notes.pdf":"9","Makefile":"10",".hidden.txt":"11","dl.pdf.part":"12","data.csv":"13"})
T("S","S01","version prints",lambda:(org(None,"--version",age0=False)[1].strip().endswith("2.7"),""))
T("S","S02","help works",lambda:(org(None,"--help",age0=False)[0]==0,""))
before=allf(S); org(S,"-n"); T("S","S03","dry-run moves nothing",lambda:(allf(S)==before,""))
rc,o=org(S); a=lambda n,top:(lambda f:(bool(f and f.startswith(top)),f))(find(S,n))
T("S","S04","real run exit 0, 0 errors",lambda:(rc==0 and " 0 errors" in o,o.strip().splitlines()[-1][-60:]))
T("S","S05","pdf -> Documents",lambda:a("report.pdf","Documents"))
T("S","S06","jpg -> Images",lambda:a("photo.jpg","Images"))
T("S","S07","mp4 -> Videos",lambda:a("movie.mp4","Videos"))
T("S","S08","mp3 -> Audio",lambda:a("song.mp3","Audio"))
T("S","S09","c -> Code",lambda:a("main.c","Code"))
T("S","S10","zip -> Archives",lambda:a("archive.zip","Archives"))
T("S","S11","exe -> Installers",lambda:a("setup.exe","Installers"))
T("S","S12","Screenshot -> Images",lambda:a("Screenshot 2026-01-01 at 10.00.00.png","Images"))
T("S","S13","topic RTOS file in RTOS path",lambda:("RTOS" in (find(S,"RTOS_notes.pdf") or ""),find(S,"RTOS_notes.pdf")))
T("S","S14","Makefile -> Code/Build",lambda:a("Makefile","Code/Build"))
T("S","S15","hidden file left alone",lambda:(os.path.exists(S+"/.hidden.txt"),""))
T("S","S16",".part partial left alone",lambda:(os.path.exists(S+"/dl.pdf.part"),""))
rc2,o2=org(S); T("S","S17","second run moves nothing",lambda:("0 moved" in o2,o2.strip().splitlines()[-1][-50:]))
rh,oh=org(None,"--history",age0=False); T("S","S18","--history lists run",lambda:(re.search(r"[0-9a-f]{8}",oh) is not None,""))
rc,o=org(S,"--undo"); T("S","S19","undo restores all files",lambda:(os.path.exists(S+"/report.pdf") and os.path.exists(S+"/photo.jpg") and os.path.exists(S+"/main.c"),o.strip().splitlines()[-1][-60:]))
T("S","S20","undo twice -> nothing to undo",lambda:("nothing to undo" in org(S,"--undo")[1],""))
# ---------- MEDIUM ----------
def m1():
    mk(D+"M1",{"a.pdf":"new"}); os.makedirs(D+"M1/Documents/PDF"); open(D+"M1/Documents/PDF/a.pdf","w").write("old"); org(D+"M1")
    return (open(D+"M1/Documents/PDF/a.pdf").read()=="old" and open(D+"M1/Documents/PDF/a (1).pdf").read()=="new",""),
T("M","M01","clash different content -> (1), old kept",lambda:m1()[0])
def m2():
    mk(D+"M2",{"a.pdf":"same"}); os.makedirs(D+"M2/Documents/PDF"); open(D+"M2/Documents/PDF/a.pdf","w").write("same"); org(D+"M2")
    return (find(D+"M2","a.pdf") in ("_Duplicates/a.pdf",) or any(f.startswith("_Duplicates") for f in allf(D+"M2")),allf(D+"M2"))
T("M","M02","identical copy -> _Duplicates",m2)
def m3():
    mk(D+"M3",{"y.pdf":"same"}); os.makedirs(D+"M3/Documents/PDF"); open(D+"M3/Documents/PDF/x.pdf","w").write("same"); org(D+"M3")
    return (any(f.startswith("_Duplicates") for f in allf(D+"M3")),allf(D+"M3"))
T("M","M03","same content, different name caught",m3)
def m4():
    mk(D+"M4",{"a.pdf":"1","b.pdf":"2"}); org(D+"M4"); org(D+"M4","--restore","a.pdf")
    return (os.path.exists(D+"M4/a.pdf") and not os.path.exists(D+"M4/b.pdf"),allf(D+"M4"))
T("M","M04","--restore one file only",m4)
def m5():
    mk(D+"M5",{"a.pdf":"1"}); org(D+"M5"); open(D+"M5/b.pdf","w").write("2"); org(D+"M5")
    ids=re.findall(r"\b[0-9a-f]{8}\b",org(None,"--history",age0=False)[1]); 
    # find id belonging to this folder: try undo of each id until one file returns
    got=None
    for i in dict.fromkeys(ids):
        org(D+"M5","--undo",i)
        if os.path.exists(D+"M5/a.pdf") or os.path.exists(D+"M5/b.pdf"): got=i;break
    return (os.path.exists(D+"M5/a.pdf")!=os.path.exists(D+"M5/b.pdf"),"only one run undone" )
T("M","M05","--undo RUN_ID undoes one run only",m5)
def m6():
    mk(D+"M6",{"proj/main.py":"x","proj/README.md":"r","proj/x.pdf":"p","root.pdf":"1"}); org(D+"M6","-r")
    return (os.path.exists(D+"M6/proj/x.pdf") and os.path.exists(D+"M6/proj/main.py") and not os.path.exists(D+"M6/root.pdf"),allf(D+"M6"))
T("M","M06","recursive keeps code project whole",m6)
def m7(age,expect_moved):
    p=D+f"M7{age}"; mk(p,{"holiday/a.jpg":"1","holiday/b.jpg":"2"},age_days=age); 
    for d in ("holiday",): t=time.time()-age*86400; os.utime(p+"/"+d,(t,t))
    org(p); return (os.path.isdir(p+"/holiday")!=expect_moved,[f for f in allf(p)][:2])
T("M","M07","loose folder idle 3 days gets organized",lambda:m7(3,True))
T("M","M08","fresh folder (<24h) left alone",lambda:m7(0,False))
def m9():
    mk(D+"M9",{"venv/pyvenv.cfg":"x","venv/lib/a.py":"1","node_modules/p/i.js":"1","normal/a.jpg":"1"},age_days=5)
    for d in ("venv","node_modules","normal"): t=time.time()-5*86400; os.utime(D+"M9/"+d,(t,t))
    org(D+"M9"); return (os.path.exists(D+"M9/venv/pyvenv.cfg") and os.path.exists(D+"M9/node_modules/p/i.js"),allf(D+"M9")[:4])
T("M","M09","venv / node_modules never moved",m9)
mk(D+"M10",{"a.xyz":"1","noext":"2","CON.txt":"3","NUL":"4"}); rc,o=org(D+"M10")
T("M","M10","unknown ext -> Other/XYZ",lambda:("Other/XYZ/a.xyz" in allf(D+"M10"),allf(D+"M10")))
T("M","M11","no-ext + reserved names: no errors, nothing lost",lambda:(rc==0 and len(allf(D+"M10"))==4 and " 0 errors" in o,o.strip().splitlines()[-1][-50:]))
mk(D+"M13",{"a.pdf":"1"}); org(D+"M13","--subfolders","year"); T("M","M12","--subfolders year adds year folder",lambda:(any(re.search(r"/20\d\d/",f) for f in allf(D+"M13")),allf(D+"M13")))
def m14():
    mk(D+"M14",{"a.pdf":"new"}); os.makedirs(D+"M14/Documents/PDF"); open(D+"M14/Documents/PDF/a.pdf","w").write("old"); org(D+"M14","--on-conflict","skip")
    return (os.path.exists(D+"M14/a.pdf") and open(D+"M14/Documents/PDF/a.pdf").read()=="old",allf(D+"M14"))
T("M","M13","on_conflict skip leaves file",m14)
def m15():
    mk(D+"M15",{"a.pdf":"new"}); os.makedirs(D+"M15/Documents/PDF"); open(D+"M15/Documents/PDF/a.pdf","w").write("old"); org(D+"M15","--on-conflict","overwrite")
    bk=[f for f in allf(D+"M15")+glob.glob(PK+"/history/**/*",recursive=True) if os.path.isfile(PK+"/"+f if not f.startswith("/") else f) or os.path.isfile(D+"M15/"+f)]
    old_kept=any(open(x,"rb").read()==b"old" for x in glob.glob(D+"M15/**/*",recursive=True)+glob.glob(PK+"/history/**/*",recursive=True) if os.path.isfile(x))
    return (open(D+"M15/Documents/PDF/a.pdf").read()=="new" and old_kept,"new in place, old backup kept="+str(old_kept))
T("M","M14","overwrite replaces + keeps backup",m15)
def m16():
    mk(D+"M16",{"a.pdf":"1"}); c=cfgwith(watch=[D+"M16"]); org(None,"--snooze","1h",age0=False)
    subprocess.run(["python3","organizer.py","-c",c,"-y","--all","--scheduled","--min-age","0"],cwd=PK,capture_output=True,env=ENV)
    paused_ok=os.path.exists(D+"M16/a.pdf"); org(D+"M16"); manual_ok=not os.path.exists(D+"M16/a.pdf"); org(None,"--resume",age0=False)
    return (paused_ok and manual_ok,f"scheduled skipped={paused_ok} manual moved={manual_ok}")
T("M","M15","snooze blocks scheduled, not manual",m16)
mk(D+"M17",{"a.pdf":"1"}); org(D+"M17"); od=org(None,"--doctor",age0=False)[1]
T("M","M16","--doctor shows no [X] after a good run",lambda:("[X]" not in od,[l for l in od.splitlines() if "[X]" in l][:1]))
def m18():
    mk(D+"M18",{"Installers/old.exe":"1","Installers/new.exe":"2"}); t=time.time()-40*86400; os.utime(D+"M18/Installers/old.exe",(t,t)); n=len(allf(D+"M18"))
    org(D+"M18","--archive-old"); f=allf(D+"M18"); return (any(x.startswith("Archive/") and x.endswith("old.exe") for x in f) and "Installers/new.exe" in f and len(f)==n,f)
T("M","M17","--archive-old moves only old installer, deletes nothing",m18)
c=json.load(open(PK+"/organizer_config.json")); open("/tmp/T/bom.json","w",encoding="utf-8-sig").write(json.dumps(c)); mk(D+"M19",{"a.pdf":"1"})
T("M","M18","config saved with BOM loads",lambda:(org(D+"M19",cfg="/tmp/T/bom.json")[0]==0 and not os.path.exists(D+"M19/a.pdf"),""))
open("/tmp/T/bad.json","w").write("{oops"); mk(D+"M20",{"a.pdf":"1"}); rc,o=org(D+"M20",cfg="/tmp/T/bad.json")
T("M","M19","damaged config -> message mentions repair, no traceback",lambda:("repair" in o.lower() and "Traceback" not in o,o.strip().splitlines()[-1][:60]))
mk(D+"M21",{"a.pdf":"1","b.pdf":"2"}); os.chmod(D+"M21/a.pdf",0); rc,o=org(D+"M21",user=True)
T("M","M20","unreadable file doesn't stop the run",lambda:(rc==0 and os.path.exists(D+"M21/Documents/PDF/b.pdf"),o.strip().splitlines()[-1][-50:]))
# ---------- HARD ----------
mk(D+"H1",{"a"*40+"!.txt":"x"}); bomb=cfgwith(); c=json.load(open(bomb)); c["rules"].insert(0,{"name":"bomb","regex":"^(a+)+$","dest":"Bomb","custom":True}); json.dump(c,open(bomb,"w"))
T("H","H01","catastrophic regex in user rule finishes <20 s",lambda:(org(D+"H1",cfg=bomb,to=20)[0]!="TIMEOUT","hang" ))
mk(D+"H2",{"a.pdf":"1"}); os.utime(D+"H2/a.pdf",(2209000000,2209000000)); org(D+"H2")
T("H","H02","file dated year 2040 still organized",lambda:(not os.path.exists(D+"H2/a.pdf"),"stays loose forever"))
n="x"*251+".pdf"; mk(D+"H3",{n:"new"}); os.makedirs(D+"H3/Documents/PDF"); open(D+"H3/Documents/PDF/"+n,"w").write("old"); rc,o=org(D+"H3")
T("H","H03","255-char name clash renamed OK",lambda:(os.path.exists(D+"H3/"+n)==False,"Errno 36 name too long" if os.path.exists(D+"H3/"+n) else ""))
mk(D+"H4",{"ok.pdf":"1"}); open((D+"H4/").encode()+b"bad\xff.pdf","wb").write(b"2"); rc,o=org(D+"H4")
T("H","H04","non-UTF-8 name: no logging errors",lambda:("Logging error" not in o and "UnicodeEncodeError" not in o,"UnicodeEncodeError in log" if "Unicode" in o else ""))
mk(D+"H5",{"a.pdf":"1"}); os.chmod(D+"H5",0o555); rc,o=org(D+"H5",user=True)
T("H","H05","read-only folder: message says permission",lambda:("ermission" in o,[l[9:90] for l in o.splitlines() if "a.pdf" in l or "retry" in l][:1]))
mk(D+"H6",{"a.pdf":"1"}); os.makedirs(D+"H6/Documents/PDF"); os.chmod(D+"H6/Documents/PDF",0o555); rc,o=org(D+"H6",user=True)
T("H","H06","read-only destination: message says permission",lambda:("ermission" in o,[l[9:90] for l in o.splitlines() if "retry" in l][:1]))
mk(D+"H7",{f"v{i}.pdf":str(i) for i in range(3000)}); pr=subprocess.Popen(["python3","organizer.py","-s",D+"H7","-y","--min-age","0"],cwd=PK,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV); time.sleep(0.4)
for i in range(0,3000,3):
    try: os.remove(D+f"H7/v{i}.pdf")
    except: pass
o=pr.communicate()[0].decode(); m=re.search(r"(\d+) errors",o)
T("H","H07","files vanishing mid-run not counted as errors",lambda:(m is not None and int(m.group(1))==0,f"{m.group(1) if m else '?'} errors"))
mk(D+"H8",{f"f{i}.pdf":str(i) for i in range(20)}); org(D+"H8"); h=[f for f in os.listdir(PK+"/history") if f.startswith("H8_")][0]; d=open(PK+"/history/"+h,"rb").read(); open(PK+"/history/"+h,"wb").write(d[:-25]); rc,o=org(D+"H8","--undo")
T("H","H08","truncated history: undo restores all or warns",lambda:(len([f for f in allf(D+"H8") if "/" not in f])==20 or "could not" in o and "1 could not" in o,f"{len([f for f in allf(D+'H8') if '/' not in f])}/20 back"))
mk(D+"H9",{"~$report.docx":"1","report.docx":"2"}); org(D+"H9"); T("H","H09","Office temp ~$ file ignored",lambda:(os.path.exists(D+"H9/~$report.docx"),"filed into Documents"))
mk(D+"H10",{f"f{i}.pdf":str(i) for i in range(2000)}); ps=[subprocess.Popen(["python3","organizer.py","-s",D+"H10","-y","--min-age","0"],cwd=PK,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV) for _ in range(4)]; os_=[p.communicate()[0].decode() for p in ps]
T("H","H10","4 simultaneous runs: no loss, no duplicates",lambda:(len(allf(D+"H10"))==2000 and not any("Traceback" in x for x in os_),f"{len(allf(D+'H10'))} files"))
mk(D+"H11",{"proj/main.py":"x","pic.jpg":"1"}); os.symlink(D+"H11",D+"H11/proj/loop"); os.symlink("/nonexistent",D+"H11/broken.pdf"); rc,o=org(D+"H11","-r",to=30)
T("H","H11","symlink loop + broken link: no hang/crash",lambda:(rc==0,"rc="+str(rc)))
p=D+"H12"; shutil.rmtree(p,ignore_errors=True); d=p
for i in range(300): d+="/d"
os.makedirs(d); open(d+"/a.pdf","w").write("1"); rc,o=org(p,"-r",to=30); T("H","H12","300-level deep folders",lambda:(rc==0,"rc="+str(rc)))
mk(D+"H13",{"a.pdf":"1"}); os.makedirs(D+"elsewhere",exist_ok=True); os.symlink(D+"elsewhere",D+"H13/Documents"); org(D+"H13")
T("H","H13","destination symlink: file stays inside folder",lambda:(len(os.listdir(D+"elsewhere"))==0 and len(allf(D+"H13"))==1,"uses Documents (folder)"))
import random; ext=["pdf","jpg","txt","zip","xyz","mp3","c"]; mk(D+"H14",{f"f_{i}.{random.choice(ext)}":str(i%200) for i in range(6000)}); t=time.time(); rc,o=org(D+"H14",to=120); dt=time.time()-t
T("H","H14","6000 files organized fast, 0 errors",lambda:(rc==0 and " 0 errors" in o and dt<20,f"{dt:.1f}s"))
t=time.time(); org(D+"H14","--space",age0=False); org(D+"H14","--suggest",age0=False); org(D+"H14","--find-duplicates",age0=False); dt=time.time()-t
T("H","H15","--space/--suggest/--find-duplicates on 6000 files",lambda:(dt<30,f"{dt:.1f}s"))
def kill(sig):
    mk(D+f"H{sig}",{f"k{i}.pdf":str(i) for i in range(5000)}); pr=subprocess.Popen(["python3","organizer.py","-s",D+f"H{sig}","-y","--min-age","0"],cwd=PK,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=ENV); time.sleep(0.6); pr.send_signal(sig); pr.wait()
    left=len([f for f in allf(D+f"H{sig}") if "/" not in f]); org(D+f"H{sig}","--undo"); back=len([f for f in allf(D+f"H{sig}") if "/" not in f])
    return (back==5000,f"killed with {5000-left} moved; {back}/5000 back")
T("H","H16","hard kill mid-run: everything undoable",lambda:kill(9)); T("H","H17","Ctrl+C mid-run: everything undoable",lambda:kill(2))
nfc=unicodedata.normalize("NFC","café.pdf"); nfd=unicodedata.normalize("NFD","café.pdf"); mk(D+"H18",{nfc:"same",nfd:"same"}); rc,o=org(D+"H18"); T("H","H18","NFC/NFD same name: nothing lost",lambda:(len(allf(D+"H18"))==2 and rc==0,""))
mk(D+"H19",{"a.pdf":"1","b.jpg":"2"}); org(D+"H19"); os.remove(find(D+"H19","b.jpg") and D+"H19/"+find(D+"H19","b.jpg")); open(D+"H19/a.pdf","w").write("NEW"); rc,o=org(D+"H19","--undo")
T("H","H19","undo when spot taken: no overwrite",lambda:(open(D+"H19/a.pdf").read()=="NEW" and find(D+"H19","a (1).pdf") is not None,allf(D+"H19")))
mk(D+"H20",{"Documents":"i am a file","a.pdf":"1"}); rc,o=org(D+"H20"); T("H","H20","file named like destination folder",lambda:(rc==0 and find(D+"H20","a.pdf") is not None and " 0 errors" in o,[f for f in allf(D+"H20")]))
json.dump(R,open("/tmp/results.json","w"))
print("TOTAL",{p:(sum(1 for r in R if r[0]==p and r[3] is True),sum(1 for r in R if r[0]==p)) for p in "SMH"})
