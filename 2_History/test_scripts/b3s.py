exec(open("/home/claude/t/pre3.py").read()); D="/tmp/T6/"; shutil.rmtree(D,ignore_errors=True); os.makedirs(D); os.chmod(D,0o777)
# A: 40 more extensions
X=[("docm xlsm odp ods epub","Documents"),("raw cr2 nef psd ai eps jfif","Images"),("m4v mpg mpeg 3gp","Videos"),("opus aiff mid","Audio"),("cs go rs php rb swift kt sql yaml yml","Code"),("tar bz2 xz","Archives"),("iso dmg apk deb rpm hex bin elf map",None)]
i=0; dests={}
for exts,top in X:
    for e in exts.split():
        i+=1; p=D+f"a{i}"; mk(p,{f"sample.{e}":"x"}); rc,o=org(p); f=find(p,f"sample.{e}"); dests[e]=f
        ok=(f is not None and "/" in f and errs0(o)) and (top is None or f.startswith(top+"/"))
        TT("S",f".{e} lands in {top or 'any folder'} (got {f.split('/')[0] if f else 'LOOSE'})",lambda ok=ok,f=f:(ok,f))
# B: 20 name variants
N=[("a.pdf","Documents"),("A.PDF","Documents"),("report.final.v2.pdf","Documents"),("my report (1).pdf","Documents"),("2024-report.pdf","Documents"),("report-final_FINAL.pdf","Documents"),("x.backup.pdf","Documents"),("file.name.with.dots.jpg","Images"),("IMG_0001.JPG","Images"),("photo copy.jpeg","Images"),("song - artist.mp3","Audio"),("movie.2024.1080p.mkv","Videos"),("archive.tar.gz","Archives"),("notes.TXT","Documents"),("main.C","Code"),("Setup-1.2.3.exe","Installers"),("data(2).csv","Documents"),("résumé.pdf","Documents"),("a b c.xlsx","Documents"),("ÜBER.PNG","Images")]
for n,top in N:
    p=D+f"b{abs(hash(n))}"; mk(p,{n:"x"}); rc,o=org(p); f=find(p,n)
    TT("S",f"name variant {n[:26]} -> {top}",lambda f=f,top=top,o=o:(bool(f and f.startswith(top+"/") and errs0(o)),f))
# C: 20 CLI behaviours
p=D+"c"; mk(p,{"a.pdf":"1","b.jpg":"2"}); ago(p+"/a.pdf",1); ago(p+"/b.jpg",1)
C=[(["--version"],0),(["-h"],0),(["--doctor"],0),(["--status"],0),(["--space"],0),(["--suggest"],0),(["--history"],0),(["--clean-empty"],0),(["-v","-n"],0),(["--snooze","5m"],0),(["--resume"],0),(["--find-duplicates"],0),(["--archive-old","-n"],0),(["--subfolders","year-month","-n"],0),(["--on-conflict","skip","-n"],0),(["--min-age","5","-n"],0),(["--bogus"],2),(["--on-conflict","weird"],2),(["--snooze","abc"],1),(["--min-age","abc"],2)]
for a,exp in C:
    def f(a=a,exp=exp):
        r=subprocess.run(["python3","organizer.py","-s",p]+a,cwd=PK,capture_output=True,env=ENV,timeout=60,input=b""); o=(r.stdout+r.stderr).decode("utf8","replace"); return (r.returncode==exp and "Traceback" not in o),f"rc={r.returncode} want {exp}"
    TT("S","CLI "+" ".join(a),f)
def f():
    r=subprocess.run(["python3","organizer.py","-s","/tmp/does/not/exist","-y"],cwd=PK,capture_output=True,env=ENV); o=(r.stdout+r.stderr).decode(); return r.returncode==1 and "Traceback" not in o,f"rc={r.returncode}"
TT("S","CLI missing source folder",f)
# D: 10 undo cycles + 10 dry-runs (per category)
CAT=[("pdf","a.pdf"),("jpg","a.jpg"),("mp4","a.mp4"),("mp3","a.mp3"),("c","a.c"),("zip","a.zip"),("exe","a.exe"),("csv","a.csv"),("txt","a.txt"),("docx","a.docx")]
for e,n in CAT:
    p=D+f"u{e}"; mk(p,{n:"1"}); org(p); org(p,"--undo"); TT("S",f"organize then undo ({e})",lambda p=p,n=n:(os.path.exists(p+"/"+n),allf(p)))
for e,n in CAT:
    p=D+f"d{e}"; mk(p,{n:"1"}); rc,o=org(p,"-n"); TT("S",f"dry-run shows plan, moves nothing ({e})",lambda p=p,n=n,o=o:(os.path.exists(p+"/"+n) and n in o,allf(p)))
save("b3s")
json.dump(dests,open("/tmp/dests.json","w"))
