s=open("big.py").read().split("# ---------- SIMPLE ----------")[0]
exec(s); D="/tmp/T2/"; shutil.rmtree(D,ignore_errors=True); os.makedirs(D); os.chmod(D,0o777)
R2=[]
def T(pri,id,desc,fn):
    try: ok,note=fn()
    except Exception as e: ok,note="ERR",repr(e)[:90]
    R2.append((pri,id,desc,ok,str(note)[:80]))
    if ok is not True: print(pri,id,"PASS" if ok is True else ("FAIL" if ok is False else ok),desc[:45],"|",str(note)[:75],flush=True)
def ago(p,days): t=time.time()-days*86400; os.utime(p,(t,t))
# ---------- SIMPLE 50: extension -> expected top folder ----------
EXP={"Documents":"pdf docx doc pptx ppt xlsx xls csv xml txt md rtf odt","Images":"jpg jpeg png gif bmp webp svg heic tiff","Videos":"mp4 mkv avi mov wmv webm","Audio":"mp3 wav flac aac ogg m4a","Code":"py c h cpp java js ts html css json","Archives":"zip rar 7z gz","Installers":"exe msi"}
n=0
for top,exts in EXP.items():
    for e in exts.split():
        n+=1; E=e.upper() if n%2 else e; p=D+f"S{n}"; mk(p,{f"sample file.{E}":"x"+str(n)}); org(p)
        T("S",f"S{n+20:02d}" if False else f"S2-{n:02d}",f".{E} -> {top}",lambda p=p,E=E,top=top:((lambda f:(bool(f and f.startswith(top+"/")),f))(find(p,f"sample file.{E}"))))
# ---------- MEDIUM 50 ----------
c=0
def MID(desc,fn):
    global c; c+=1; T("M",f"M2-{c:02d}",desc,fn)
OLD=1709600000  # 2024-03-05
for opt,chk in [("extension",None),("year","2024"),("month",None),("year-month","2024-03"),("first-letter","R"),("size",None),("topic",None)]:
    for fn,top in [("report.pdf","Documents"),("riverside.jpg","Images")]:
        def f(opt=opt,chk=chk,fn=fn,top=top):
            p=D+f"MS_{opt}_{fn}"; mk(p,{fn:"x"}); os.utime(p+"/"+fn,(OLD,OLD)); rc,o=org(p,"--subfolders",opt); r=find(p,fn)
            ok=rc==0 and r is not None and r.startswith(top) and " 0 errors" in o and (chk is None or chk in r); return ok,r
        MID(f"--subfolders {opt} on {fn}",f)
def conf(mode,same):
    p=D+f"MC_{mode}_{same}"; mk(p,{"a.pdf":"new"}); os.makedirs(p+"/Documents/PDF"); open(p+"/Documents/PDF/a.pdf","w").write("new" if same else "old"); org(p,"--on-conflict",mode)
    fs=allf(p); allc=[open(p+"/"+x,"rb").read() for x in fs]
    return fs,allc
def mc(mode,same,check): 
    def f(): fs,allc=conf(mode,same); return check(fs,allc),fs
    return f
nl=lambda fs,al:b"old" in al and b"new" in al
MID("rename + different -> both kept",mc("rename",False,lambda fs,al:b"old" in al and b"new" in al and len(fs)==2))
MID("rename + identical -> one kept, 1 dup set aside",mc("rename",True,lambda fs,al:len(fs)==2 and any(x.startswith("_Duplicates") for x in fs)))
MID("skip + different -> new stays loose",mc("skip",False,lambda fs,al:"a.pdf" in fs and b"old" in al))
MID("skip + identical -> nothing lost",mc("skip",True,lambda fs,al:len(fs)>=1 and b"new" in al))
MID("overwrite + different -> new in place",mc("overwrite",False,lambda fs,al:open(D+"MC_overwrite_False/Documents/PDF/a.pdf").read()=="new"))
MID("overwrite + identical -> content intact",mc("overwrite",True,lambda fs,al:b"new" in al))
def ign(pat,files,stay):
    def f():
        p=D+f"MI{abs(hash(pat))}"; cfg=cfgwith(ignore_patterns=json.load(open(PK+"/organizer_config.json"))["ignore_patterns"]+[pat]); mk(p,files); rc,o=org(p,cfg=cfg)
        return all(os.path.exists(p+"/"+x) for x in stay) and not any(os.path.exists(p+"/"+x) for x in files if x not in stay),allf(p)
    return f
MID("ignore pattern secret*",ign("secret*",{"secret1.pdf":"1","ok.pdf":"2"},["secret1.pdf"]))
MID("ignore pattern *.tmp2",ign("*.tmp2",{"a.tmp2":"1","a.pdf":"2"},["a.tmp2"]))
MID("ignore pattern with ?",ign("Doc?.pdf",{"Doc1.pdf":"1","Docs12.pdf":"2"},["Doc1.pdf"]))
MID("ignore exact name",ign("keep.pdf",{"keep.pdf":"1","go.pdf":"2"},["keep.pdf"]))
MID("built-in *password*.csv ignored",ign("zzz_none",{"my password list.csv":"1","data.csv":"2"},["my password list.csv"]))
def sz(rule,files,expect):
    def f():
        p=D+f"MZ{abs(hash(str(rule)))}"; cfg=cfgwith(); c0=json.load(open(cfg)); c0["rules"].insert(0,dict(rule,custom=True)); json.dump(c0,open(cfg,"w"))
        mk(p,{k:(b"x"*v) for k,v in files.items()}); org(p,cfg=cfg); return all((find(p,k) or "").startswith(v) for k,v in expect.items()),{k:find(p,k) for k in expect}
    return f
MID("size rule min_size_mb",sz({"name":"big","extensions":["pdf"],"min_size_mb":1,"dest":"Big"},{"big.pdf":2*1024*1024,"small.pdf":1000},{"big.pdf":"Big","small.pdf":"Documents"}))
MID("size rule max_size_mb",sz({"name":"tiny","extensions":["pdf"],"max_size_mb":0.01,"dest":"Tiny"},{"big.pdf":2*1024*1024,"small.pdf":1000},{"big.pdf":"Documents","small.pdf":"Tiny"}))
MID("size rule min+max (between)",sz({"name":"mid","extensions":["pdf"],"min_size_mb":0.5,"max_size_mb":3,"dest":"Mid"},{"a.pdf":1024*1024,"b.pdf":10,"c.pdf":5*1024*1024},{"a.pdf":"Mid","b.pdf":"Documents","c.pdf":"Documents"}))
MID("size rule no match leaves default",sz({"name":"huge","extensions":["pdf"],"min_size_mb":100,"dest":"Huge"},{"a.pdf":10},{"a.pdf":"Documents"}))
MID("regex rule ^invoice_\\d+",sz({"name":"inv","regex":"^invoice_\\d+","dest":"Invoices"},{"invoice_123.pdf":5,"my_invoice.pdf":5},{"invoice_123.pdf":"Invoices","my_invoice.pdf":"Documents"}))
MID("regex rule is case sensitive?",sz({"name":"inv","regex":"^Invoice","dest":"Invoices"},{"Invoice1.pdf":5,"invoice2.pdf":5},{"Invoice1.pdf":"Invoices"}))
MID("regex no match falls through",sz({"name":"inv","regex":"^zzz$","dest":"Z"},{"a.pdf":5},{"a.pdf":"Documents"}))
MID("glob pattern report_*.pdf",sz({"name":"rep","patterns":["report_*.pdf"],"dest":"Reports"},{"report_1.pdf":5,"other.pdf":5},{"report_1.pdf":"Reports","other.pdf":"Documents"}))
MID("glob pattern *final*",sz({"name":"fin","patterns":["*final*"],"dest":"Finals"},{"thesis final v2.docx":5,"thesis.docx":5},{"thesis final v2.docx":"Finals","thesis.docx":"Documents"}))
MID("glob pattern ?.txt",sz({"name":"one","patterns":["?.txt"],"dest":"One"},{"a.txt":5,"ab.txt":5},{"a.txt":"One","ab.txt":"Documents"}))
MID("custom rule beats built-in",sz({"name":"mine","extensions":["pdf"],"dest":"MyPDFs"},{"a.pdf":5},{"a.pdf":"MyPDFs"}))
MID("disabled custom rule ignored",sz({"name":"mine","extensions":["pdf"],"dest":"MyPDFs","enabled":False},{"a.pdf":5},{"a.pdf":"Documents"}))
def age(days,args,moved):
    def f():
        p=D+f"MA{days}{len(args)}"; mk(p,{"a.pdf":"1"}); ago(p+"/a.pdf",days)
        subprocess.run(["python3","organizer.py","-s",p,"-y"]+args,cwd=PK,capture_output=True,env=ENV); return (not os.path.exists(p+"/a.pdf"))==moved,allf(p)
    return f
MID("default min-age: fresh file stays",age(0,[],False))
MID("default min-age: 2-min-old file moves",age(0.0015,[],True))
MID("--min-age 0: fresh file moves",age(0,["--min-age","0"],True))
def und(setup,args=()):
    def f():
        p=D+f"MU{abs(hash(setup.__name__+str(args)))}"; before=setup(p); org(p,*args); org(p,"--undo"); return sorted(f for f in allf(p) if not f.startswith(("_","Doc","Im","Co","Au","Vi","Ar","In","Ot")) )==sorted(before) or sorted(allf(p))==sorted(before) or all(os.path.exists(p+"/"+x) for x in before),allf(p)[:4]
    return f
def s1(p): mk(p,{"a.pdf":"1","b.jpg":"2","c.mp3":"3"}); return ["a.pdf","b.jpg","c.mp3"]
def s2(p): mk(p,{"a.pdf":"1"}); os.makedirs(p+"/Documents/PDF"); open(p+"/Documents/PDF/a.pdf","w").write("2"); return ["a.pdf"]
def s3(p): mk(p,{"a.pdf":"1","b.pdf":"1","c.pdf":"1"}); return ["a.pdf","b.pdf","c.pdf"]
MID("undo after --subfolders year-month",und(s1,("--subfolders","year-month")))
MID("undo after rename-conflict",und(s2))
MID("undo after duplicates set aside",und(s3))
def f():
    p=D+"MU4"; mk(p,{"a.pdf":"1","b.pdf":"2"}); org(p); org(p,"--restore","a.pdf"); org(p,"--undo"); return all(os.path.exists(p+"/"+x) for x in ["a.pdf","b.pdf"]),allf(p)
MID("undo after a partial --restore",f)
def f():
    p=D+"MU5"; mk(p,{"a.pdf":"1"}); org(p); open(p+"/b.pdf","w").write("2"); org(p); org(p,"--undo"); org(p,"--undo"); return all(os.path.exists(p+"/"+x) for x in ["a.pdf","b.pdf"]),allf(p)
MID("two runs, undo twice restores both",f)
def f():
    p=D+"MD1"; mk(p,{"a.pdf":"same","b.pdf":"same"}); before=allf(p); org(p,"--find-duplicates",age0=False); return allf(p)==before,"report only"
MID("--find-duplicates alone moves nothing",f)
def f():
    p=D+"MD2"; mk(p,{"a.pdf":"same","b.pdf":"same"}); org(p,"--find-duplicates","--set-aside"); fs=allf(p); return len(fs)==2 and any(x.startswith("_Duplicates") for x in fs),fs
MID("--set-aside keeps one, moves the other",f)
def f():
    p=D+"MD3"; mk(p,{"a.pdf":"same","b.pdf":"same","c.pdf":"same"}); org(p,"--find-duplicates","--set-aside"); fs=allf(p); return sum(x.startswith("_Duplicates") for x in fs)==2,fs
MID("3 identical copies -> 2 set aside",f)
def f():
    p=D+"MD4"; mk(p,{"a.pdf":"AAAA","b.pdf":"BBBB"}); org(p,"--find-duplicates","--set-aside"); return not any(x.startswith("_Duplicates") for x in allf(p)),allf(p)
MID("same size, different content not duplicates",f)
def f():
    p=D+"MD5"; mk(p,{"a.pdf":"","b.pdf":"","c.pdf":"x"}); rc,o=org(p,"--find-duplicates","--set-aside"); return rc==0 and "Traceback" not in o and len(allf(p))==3,allf(p)
MID("empty (0-byte) files handled safely",f)
json.dump(R2,open("/tmp/results_b2a.json","w"))
for lvl in "SM": print("TOTAL",lvl,sum(1 for r in R2 if r[0]==lvl and r[3] is True),"/",sum(1 for r in R2 if r[0]==lvl))
