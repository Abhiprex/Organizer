import os; os.environ["PK"]=os.environ.get("PK","/tmp/nb271")
exec(open("/home/claude/t/pre3.py").read()); D="/tmp/V/"; shutil.rmtree(D,ignore_errors=True); os.makedirs(D); os.chmod(D,0o777)
def cfgx(**kw):
    c=json.load(open(PK+"/organizer_config.json")); c.update(kw); n=f"/tmp/V/c{time.time_ns()}.json"; json.dump(c,open(n,"w")); return n
def V(n,desc,fn):
    try: ok,note=fn()
    except Exception as e: ok,note="ERR",repr(e)[:90]
    print(f"{n:>2} {'PASS' if ok is True else 'FAIL' if ok is False else ok} {desc[:52]} | {str(note)[:70]}",flush=True)
def f1():
    p=D+"1"; mk(p,{"a"*40+"!.txt":"x","ok.pdf":"1"}); c=cfgx(); j=json.load(open(c)); j["rules"].insert(0,{"name":"bomb","regex":"^(a+)+$","dest":"Bomb","custom":True}); json.dump(j,open(c,"w"))
    rc,o=org(p,cfg=c,to=30); return rc!="TIMEOUT" and find(p,"ok.pdf") is not None,"finished; other files still sorted"
V(1,"bad regex no longer hangs",f1)
def f1b():
    p=D+"1b"; mk(p,{"a"*45+"!.txt":"x"}); c=cfgx(); j=json.load(open(c)); j["rules"].insert(0,{"name":"bomb2","regex":"^(a|aa)+$","dest":"Bomb","custom":True}); json.dump(j,open(c,"w"))
    t=time.time(); rc,o=org(p,cfg=c,to=30); return rc!="TIMEOUT" and time.time()-t<15,f"{time.time()-t:.1f}s (alternation bomb stopped by the 1 s limit)"
V("1b","slow regex without nesting stopped by time limit",f1b)
mk(D+"2",{"Makefile":"x"}); org(D+"2"); V(2,"Makefile sorted to Code/Build",lambda:((find(D+"2","Makefile") or "").startswith("Code/Build"),find(D+"2","Makefile")))
def f3():
    n="x"*251+".pdf"; p=D+"3"; mk(p,{n:"new"}); os.makedirs(p+"/Documents/PDF"); open(p+"/Documents/PDF/"+n,"w").write("old"); rc,o=org(p); fs=allf(p); return (len(fs)==2 and not os.path.exists(p+"/"+n) and errs0(o)),[len(os.path.basename(x).encode()) for x in fs]
V(3,"255-char clash renamed within the limit",f3)
mk(D+"4",{"a.pdf":"1"}); os.utime(D+"4/a.pdf",(4102444800,4102444800)); org(D+"4"); V(4,"future-dated file organized",lambda:(not os.path.exists(D+"4/a.pdf"),allf(D+"4")))
def f5():
    p=D+"5"; mk(p,{"ok.pdf":"1"}); open((p+"/").encode()+b"bad\xff.pdf","wb").write(b"2"); rc,o=org(p); return ("Logging error" not in o and "UnicodeEncodeError" not in o and errs0(o)),o.strip().splitlines()[-1][-40:]
V(5,"non-UTF-8 name: clean log",f5)
def f6():
    p=D+"6"; mk(p,{f"v{i}.pdf":str(i) for i in range(3000)}); pr=subprocess.Popen(["python3","organizer.py","-s",p,"-y","--min-age","0"],cwd=PK,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,env=ENV); time.sleep(0.5)
    for i in range(0,3000,3):
        for q in (f"{p}/v{i}.pdf",f"{p}/Documents/PDF/v{i}.pdf"):
            try: os.remove(q)
            except OSError: pass
    o=pr.communicate()[0].decode(); m=re.search(r"(\d+) errors",o); return (m and int(m.group(1))==0),o.strip().splitlines()[-1][-70:]
V(6,"vanished files not counted as errors",f6)
def f7():
    p=D+"7"; mk(p,{"a.pdf":"1"}); os.chmod(p,0o555); rc,o=org(p,user=True); return "permission denied" in o,[l[9:80] for l in o.splitlines() if "permission" in l][:1]
V(7,"permission error says permission denied",f7)
def f8():
    p=D+"8"; mk(p,{f"f{i}.pdf":str(i) for i in range(20)}); org(p); h=[x for x in os.listdir(PK+"/history") if x.startswith("8_")][0]; d=open(PK+"/history/"+h,"rb").read(); open(PK+"/history/"+h,"wb").write(d[:-25]); rc,o=org(p,"--undo")
    return "damaged line" in o and "NOT put back" in o,o.strip().splitlines()[-1][-70:]
V(8,"damaged history line: clear warning at undo",f8)
mk(D+"9",{"~$report.docx":"1","report.docx":"2"}); org(D+"9"); V(9,"~$ temp file ignored",lambda:(os.path.exists(D+"9/~$report.docx"),allf(D+"9")))
def f10a():
    p=D+"10a"; mk(p,{"a.pdf":"1"}); rc,o=org(p,"--undo","BADID"); return "nothing to undo for this folder" in o and "BADID" in o,o.strip().splitlines()[-1][-70:]
V("10a","--undo with unknown run id: clear message",f10a)
def f10b():
    p=D+"10b"; mk(p,{"a.pdf":"1","b.jpg":"2"}); org(p); org(p,"--undo"); return sorted(os.listdir(p))==["a.pdf","b.jpg"],os.listdir(p)
V("10b","undo leaves no empty folders",f10b)
r=subprocess.run(["python3","manage_folders.py"],cwd=PK,input=b"",capture_output=True,env=ENV); V("10c","manage_folders with no keyboard exits cleanly",lambda:(r.returncode==0 and b"Traceback" not in r.stderr,f"rc={r.returncode}"))
c=cfgx(watch=[]); r=subprocess.run(["python3","organizer.py","-c",c,"-y","--all","--scheduled"],cwd=PK,capture_output=True,env=ENV); V("10d","scheduled run with nothing to watch: no error",lambda:(r.returncode==0,f"rc={r.returncode}"))
def f10e():
    p=D+"10e"; mk(p,{"a.pdf":"1"}); r=subprocess.run(["python3","organizer.py","-s",p,"-n"],cwd=PK,capture_output=True,env=ENV); return b"--min-age 0" in (r.stdout+r.stderr),"tip shown"
V("10e","dry run on fresh files shows a hint",f10e)
def f10f():
    p=D+"10f"; mk(p,{"a.pdf":"new"}); os.makedirs(p+"/Documents/PDF"); open(p+"/Documents/PDF/a.pdf","w").write("old"); rc,o=org(p); return "already exists" in o and "a (1).pdf" in o,"rename logged"
V("10f","name clash logs 'saved as a (1).pdf'",f10f)
def f11():
    bad=[]
    for e,top in [("html","Code"),("css","Code"),("raw","Images"),("m4v","Videos"),("mid","Audio"),("go","Code"),("sql","Code"),("docm","Documents"),("hex","Firmware"),("elf","Firmware")]:
        p=D+"11"+e; mk(p,{f"a.{e}":"1"}); org(p); r=find(p,f"a.{e}"); 
        if not (r or "").startswith(top): bad.append(e)
    return not bad,bad
V("11/18","new file types sorted (10 checked)",f11)
def f12():
    p=D+"12"; mk(p,{"a.pdf":"1"}); c=cfgx(); j=json.load(open(c)); j["rules"].insert(0,{"name":"mine","extensions":["pdf"],"dest":"MyPDFs","custom":True}); json.dump(j,open(c,"w")); rc,o=org(p,cfg=c); return (find(p,"a.pdf") or "").startswith("MyPDFs"),"dot added automatically"
V(12,"extension written without a dot still works",f12)
def f14():
    p=D+"14"; mk(p,{"a.pdf":"1"}); os.system(f"chmod -R 555 {PK}/history"); rc,o=org(p,user=True); os.system(f"chmod -R 777 {PK}/history")
    return (os.path.exists(p+"/a.pdf") and "read-only" in o and not os.path.exists(p+"/.organizer_history.jsonl")),o.strip().splitlines()[-1][:70]
V(14,"read-only Organizer folder: stops clearly",f14)
def f15():
    res=[]
    for dest in ["../../escaped","/tmp/abs_t"]:
        shutil.rmtree("/tmp/escaped",ignore_errors=True); shutil.rmtree("/tmp/abs_t",ignore_errors=True); p=D+"15/in"; mk(p,{"a.pdf":"1"}); c=cfgx(); j=json.load(open(c)); j["rules"].insert(0,{"name":"esc","extensions":[".pdf"],"dest":dest,"custom":True}); json.dump(j,open(c,"w")); rc,o=org(p,cfg=c)
        res.append(os.path.exists("/tmp/escaped") or os.path.exists("/tmp/abs_t") or os.path.exists(p+"/a.pdf")==False and not find(p,"a.pdf"))
    shutil.rmtree("/tmp/abs_t",ignore_errors=True); p=D+"15/in2"; mk(p,{"a.pdf":"1"}); c=cfgx(); j=json.load(open(c)); j["rules"].insert(0,{"name":"ok","extensions":[".pdf"],"dest":"/tmp/abs_t","allow_outside":True,"custom":True}); json.dump(j,open(c,"w")); org(p,cfg=c); allowed=os.path.exists("/tmp/abs_t/a.pdf"); shutil.rmtree("/tmp/abs_t",ignore_errors=True)
    return (not any(res) and allowed),f"blocked={not any(res)}, allow_outside works={allowed}"
V(15,"rule destination outside folder blocked unless allow_outside",f15)
def f16():
    p=D+"16"; mk(p,{f"k{i}.pdf":str(i) for i in range(3000)}); pr=subprocess.Popen(["python3","organizer.py","-s",p,"-y","--min-age","0"],cwd=PK,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=ENV); time.sleep(0.6); pr.send_signal(9); pr.wait()
    rc,o=org(p); loose=len([f for f in os.listdir(p) if f.endswith(".pdf")]); return loose==0 and cnt(p)==3000,f"loose after rerun={loose}"
V(16,"re-run right after a kill finishes the job",f16)
def f17():
    bad=0
    for i,d in enumerate([0.5,0.7,0.9,1.1,1.3,0.6,0.8,1.0,1.2,1.4]):
        p=D+f"17_{i}"; mk(p,{f"k{j}.pdf":str(j%97) for j in range(4000)}); pr=subprocess.Popen(["python3","organizer.py","-s",p,"-y","--min-age","0"],cwd=PK,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,env=ENV); time.sleep(d); pr.send_signal(9); pr.wait()
        moved=4000-len([f for f in os.listdir(p) if f.endswith(".pdf")]); org(p,"--undo"); back=len([f for f in os.listdir(p) if f.endswith(".pdf")])
        if back!=4000 or cnt(p)!=4000: bad+=1; print("   miss",moved,back)
    return bad==0,f"{10-bad}/10 kills fully undone"
V(17,"undo after hard kill restores everything (10 kills)",f17)
def f20():
    p=D+"20"; mk(p,{"a.pdf":"1","b.jpg":"2"}); org(p); os.system(f"cd {p} && mkdir Empty1 && mkdir -p Documents/Old"); rc,o=org(p,"--clean-empty","-n") if False else org(p,"--clean-empty"); return not os.path.isdir(p+"/Empty1") and not os.path.isdir(p+"/Documents/Old"),sorted(os.listdir(p))
V(20,"--clean-empty removes empty folders",f20)
