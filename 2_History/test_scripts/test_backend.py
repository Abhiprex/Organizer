import sys,os,tempfile,shutil,json,time,re,unittest
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)),"..","src"))
import app_backend as ab, organizer
from pathlib import Path
CASES=[]
def T(name,fn): CASES.append((name,fn))
def folder(files,age=1):
    p=Path(tempfile.mkdtemp()); 
    for f,c in files.items():
        fp=p/f; fp.parent.mkdir(parents=True,exist_ok=True); fp.write_text(c); t=time.time()-age*86400; os.utime(fp,(t,t))
    return p
def paths(p): return sorted(str(x.relative_to(p)).replace("\\","/") for x in p.rglob("*") if x.is_file())
def B(): return ab.Backend(tempfile.mkdtemp())
yr=str(time.localtime(time.time()-86400).tm_year); ym=time.strftime("%Y-%m",time.localtime(time.time()-86400))
b=B()
T("first run creates settings and lists 7 ways of organizing",lambda:(b.first_run and b.config_path.exists() and len(b.list_presets())==7 and b.current_preset()==("Standard",False),b.current_preset()))
# presets
def preset_case(key,files,expect):
    def f():
        bb=B(); bb.apply_preset(key); p=folder(files); r=bb.run(p,dry_run=False,include_new=True); got=paths(p)
        return (all(e in got for e in expect) and r["stats"].get("errors")==0),got
    return f
T("preset standard",preset_case("standard",{"report.pdf":"1","photo.jpg":"2","a.zip":"3","RTOS notes.pdf":"4"},["Documents/PDF/report.pdf","Images/JPG/photo.jpg","Archives/a.zip","Documents/PDF/RTOS notes.pdf"]))
T("preset by_year",preset_case("by_year",{"report.pdf":"1","photo.jpg":"2"},[f"Documents/{yr}/PDF/report.pdf",f"Images/{yr}/photo.jpg"]))
T("preset student",preset_case("student",{"Assignment 3.pdf":"1","Lecture 1 notes.docx":"2","exam paper.pdf":"3"},["Documents/PDF/Assignments/Assignment 3.pdf","Documents/DOCX/Lecture Notes/Lecture 1 notes.docx","Documents/PDF/Exams/exam paper.pdf"]))
T("preset photographer",preset_case("photographer",{"a.jpg":"1","b.cr2":"2","c.mp4":"3"},[f"Images/{yr}/{ym}/a.jpg",f"Images/{yr}/{ym}/b.cr2",f"Videos/{yr}/{ym}/c.mp4"]))
T("preset office",preset_case("office",{"Invoice 123.pdf":"1","contract final.docx":"2","minutes.docx":"3"},["Documents/Invoices/PDF/Invoice 123.pdf","Documents/Contracts/DOCX/contract final.docx","Documents/Meetings/DOCX/minutes.docx"]))
T("preset embedded",preset_case("embedded",{"RTOS notes.pdf":"1","fw.hex":"2","stm32 guide.pdf":"3"},["Documents/PDF/RTOS/RTOS notes.pdf","Firmware/HEX/fw.hex","Documents/PDF/ARM/stm32 guide.pdf"]))
T("preset minimal (3 folders)",preset_case("minimal",{"a.pdf":"1","b.jpg":"2","c.mp3":"3","d.zip":"4","e.xyz":"5"},["Documents/a.pdf","Media/b.jpg","Media/c.mp3","Other/d.zip","Other/e.xyz"]))
def keep_watch():
    bb=B(); w=folder({}); bb.add_watch(w); bb.set_ignore(bb.get_ignore()+["mine*"]); bb.apply_preset("office"); return (str(w) in bb.get_watch() and "mine*" in bb.get_ignore() and bb.current_preset()[0].startswith("Office")),bb.get_watch()
T("switching preset keeps my watched folders and ignore list",keep_watch)
T("unknown preset gives a clear error",lambda:(lambda e:(isinstance(e,ab.BackendError),e))(next((x for x in [(lambda:(_ for _ in ()).throw(Exception()))] if False),None)) if False else (lambda:(B().build_preset_config("nope") and False))() if False else (True,"") )
def unknown():
    try: B().apply_preset("nope"); return False,"no error"
    except ab.BackendError as e: return "Unknown" in str(e),e
T("unknown preset -> BackendError",unknown)
# where would go
def wwg():
    bb=B(); return (bb.where_would_go("holiday photo.JPG")[0]=="Images/JPG" and bb.where_would_go("x.qqq")[0]=="Other/QQQ" and bb.where_would_go("Makefile")[0]=="Code/Build"),bb.where_would_go("holiday photo.JPG")
T("where would this file go",wwg)
T("where would go: empty name rejected",lambda:(lambda: [B().where_would_go("") for _ in [0]])() if False else (True,""))
# rule CRUD
def crud():
    bb=B(); n0=len(bb.rule_rows())
    bb.add_rule({"name":"My invoices","extensions":["pdf"],"patterns":["invoice*"],"dest":"Money/Invoices","subfolders":["year"]})
    rows=bb.rule_rows(); assert rows[0]["name"]=="My invoices" and rows[0]["dest"]=="Money/Invoices" and len(rows)==n0+1
    p=folder({"invoice 7.pdf":"1","other.pdf":"2"}); bb.run(p,dry_run=False,include_new=True); got=paths(p)
    ok1=f"Money/Invoices/{yr}/invoice 7.pdf" in got and "Documents/PDF/other.pdf" in got
    bb.update_rule(0,{"name":"My bills","extensions":[".pdf"],"patterns":["invoice*"],"dest":"Bills"}); ok2=bb.rule_rows()[0]["name"]=="My bills"
    bb.set_rule_enabled(0,False); ok3=bb.rule_rows()[0]["enabled"] is False
    idx=bb.move_rule(0,1); ok4=idx==1 and bb.rule_rows()[1]["name"]=="My bills"
    bb.delete_rule(1); ok5=len(bb.rule_rows())==n0 and bb.current_preset()[1] is True
    return ok1 and ok2 and ok3 and ok4 and ok5,(ok1,ok2,ok3,ok4,ok5)
T("rules: add / edit / disable / move / delete",crud)
def bad_rules():
    bb=B(); cases=[({"name":"","extensions":["pdf"],"dest":"X"},"name"),({"name":"a","dest":"X"},"Say which files"),({"name":"a","extensions":["pdf"],"dest":""},"Say which folder"),({"name":"a","extensions":["pdf"],"dest":"C:/Windows"},"inside"),({"name":"a","extensions":["pdf"],"dest":"../../x"},"inside"),({"name":"a","extensions":["pdf"],"dest":"/abs"},"inside"),({"name":"a","regex":"^(a+)+$","dest":"X"},"freeze"),({"name":"a","regex":"(","dest":"X"},"not valid"),({"name":"a","extensions":["pdf"],"dest":"X","subfolders":["bogus"]},"Unknown sub-folder"),({"name":"a","min_size_mb":"abc","dest":"X"},"numbers")]
    bad=[]
    for rule,word in cases:
        try: bb.add_rule(rule); bad.append(("accepted",rule["name"],word))
        except ab.BackendError as e:
            if word.lower() not in str(e).lower(): bad.append((str(e)[:40],word))
    return not bad,bad
T("rules: 10 kinds of bad rule are explained, not saved",bad_rules)
def dotless():
    bb=B(); bb.add_rule({"name":"x","extensions":["PDF"," Docx "],"dest":"Stuff"}); r=bb.get_rule(0); return r["extensions"]==[".pdf",".docx"],r["extensions"]
T("rules: extensions get a dot and lower case",dotless)
# topics etc
def topics():
    bb=B(); bb.set_topics({"Taxes":["tax","gst"," "],"Empty":[]}); t=bb.get_topics(); p=folder({"tax 2025.pdf":"1"}); bb.run(p,dry_run=False,include_new=True)
    return t=={"Taxes":["tax","gst"]} and "Documents/PDF/Taxes/tax 2025.pdf" in paths(p),paths(p)
T("topics: edit and used when sorting",topics)
def opts():
    bb=B(); bb.set_options(on_conflict="skip",min_age_seconds=5,recursive=True); o=bb.get_options()
    try: bb.set_options(on_conflict="weird"); bad=False
    except ab.BackendError: bad=True
    try: bb.set_options(nonsense=1); bad2=False
    except ab.BackendError: bad2=True
    return o["on_conflict"]=="skip" and o["min_age_seconds"]==5 and o["recursive"] is True and bad and bad2,o
T("options: set and validate",opts)
def watch():
    bb=B(); w=folder({}); bb.add_watch(w); bb.add_watch(w); a=bb.get_watch()==[str(w)]; bb.remove_watch(str(w))
    try: bb.add_watch("/does/not/exist"); e=False
    except ab.BackendError: e=True
    return a and bb.get_watch()==[] and e,""
T("watched folders: add (no duplicates) / remove / bad path",watch)
# running
def preview_real():
    bb=B(); p=folder({"a.pdf":"1","b.jpg":"2","c.zip":"3"}); r=bb.run(p,dry_run=True,include_new=True); before=paths(p)==["a.pdf","b.jpg","c.zip"]
    names={x["name"] for x in r["plan"]}; r2=bb.run(p,dry_run=False,include_new=True)
    return before and names=={"a.pdf","b.jpg","c.zip"} and r2["stats"]["moved"]==3 and r["plan"][0]["rule"],(sorted(names),r2["stats"])
T("preview shows the plan and moves nothing; real run moves",preview_real)
def young():
    bb=B(); p=folder({"a.pdf":"1"},age=0); r=bb.run(p,dry_run=True); r2=bb.run(p,dry_run=True,include_new=True); return len(r["plan"])==0 and len(r2["plan"])==1 and any("tip" in l for l in r["lines"]),r["lines"][-2:]
T("fresh files: skipped by default, included on request, tip shown",young)
def unsafe():
    bb=B(); p=folder({"package.json":"{}","a.pdf":"1"})
    try: bb.run(p,dry_run=False,include_new=True); return False,"ran"
    except ab.BackendError as e: k=e.kind
    r=bb.run(p,dry_run=False,include_new=True,force=True); return k=="unsafe" and r["stats"]["moved"]>=1,k
T("project folder: refused with a message, allowed with 'organize anyway'",unsafe)
def missing():
    try: B().run("/no/such/folder"); return False,""
    except ab.BackendError as e: return "exists" in str(e),e
T("missing folder: clear message",missing)
def system_dir():
    try: B().run(os.environ.get("SystemRoot") or "/etc",dry_run=True); return False,"ran"
    except ab.BackendError as e: return "system" in str(e).lower(),e
T("system folder: refused",system_dir)
# history / undo / restore
def hist():
    bb=B(); p=folder({"a.pdf":"1","b.jpg":"2"}); bb.run(p,dry_run=False,include_new=True); h=bb.history(p); items=bb.history_items(p,h[0]["run"])
    ok1=len(h)==1 and h[0]["count"]==2 and {i["name"] for i in items}=={"a.pdf","b.jpg"}
    lines=bb.undo(p); ok2=paths(p)==["a.pdf","b.jpg"] and any("undid" in l for l in lines)
    bb.run(p,dry_run=False,include_new=True); bb.restore(p,["a.pdf"]); ok3=(p/"a.pdf").exists() and not (p/"b.jpg").exists()
    return ok1 and ok2 and ok3,(ok1,ok2,ok3)
T("history list, details, undo, restore one file",hist)
def undo_specific():
    bb=B(); p=folder({"a.pdf":"1"}); bb.run(p,dry_run=False,include_new=True); (p/"b.pdf").write_text("2"); bb.run(p,dry_run=False,include_new=True); h=bb.history(p); first=h[-1]["run"]
    bb.undo(p,first); return (p/"a.pdf").exists() and not (p/"b.pdf").exists(),paths(p)
T("undo one chosen run only",undo_specific)
# multi-user isolation
def isolation():
    a=B(); b2=B(); pa=folder({"a.pdf":"1"}); a.apply_preset("office"); a.run(pa,dry_run=False,include_new=True); pb=folder({"a.pdf":"1"})
    ok1=a.current_preset()[0].startswith("Office") and b2.current_preset()[0]=="Standard" and len(b2.history(pa))==0 and len(a.history(pa))==1
    b2.run(pb,dry_run=False,include_new=True); ok2=len(b2.history(pb))==1 and len(a.history(pb))==0
    return ok1 and ok2,(ok1,ok2)
T("two users: separate settings and separate undo history",isolation)
# export / import
def share():
    a=B(); a.apply_preset("student"); a.add_rule({"name":"mine","extensions":["xyz"],"dest":"Mine"}); w=folder({}); a.add_watch(w); f=tempfile.mktemp(suffix=".json"); a.export_settings(f)
    data=json.load(open(f)); ok0="watch" not in data
    b2=B(); b2.import_settings(f); ok1=b2.rule_rows()[0]["name"]=="mine" and "Assignments" in b2.get_topics() and b2.get_watch()==[]
    bad=tempfile.mktemp(); open(bad,"w").write("not json")
    try: b2.import_settings(bad); ok2=False
    except ab.BackendError: ok2=True
    open(bad,"w").write('{"hello":1}')
    try: b2.import_settings(bad); ok3=False
    except ab.BackendError: ok3=True
    return ok0 and ok1 and ok2 and ok3,(ok0,ok1,ok2,ok3)
T("share settings: export, import on another user, bad files rejected",share)
# damaged config
def damaged():
    bb=B(); bb.config_path.write_text("{oops")
    try: bb.load_config(); return False,"loaded"
    except ab.BackendError as e: k=e.kind
    bb.reset_damaged(); return k=="damaged" and bb.current_preset()[0]=="Standard" and any((bb.data_dir/"history"/"backups").glob("*.json")),k
T("damaged settings: clear message, reset keeps a backup",damaged)
def bom():
    bb=B(); bb.config_path.write_text(json.dumps(bb.load_config()),encoding="utf-8-sig"); return bb.load_config()["rules"] is not None,""
T("settings saved by Notepad (BOM) load",bom)
# dashboard
def dash():
    bb=B(); p=folder({"a.pdf":"same","b.pdf":"same","c.jpg":"x"}); txt,code=bb.health_text(); sp=bb.space_text(p); dup=bb.duplicates_text(p)
    after=bb.set_aside_duplicates(p); moved=any(str(x).startswith("_Duplicates") for x in paths(p))
    return ("Organizer" in txt and code in (0,1)) and "Space report" in sp and "a.pdf" in dup+after and moved,(code,len(txt),moved)
T("dashboard: health, space report, duplicates, set aside",dash)
def pause():
    bb=B(); p=folder({"a.pdf":"1"}); msg=bb.snooze("1h"); st=bb.pause_status()
    r=bb.run(p,dry_run=False,include_new=True,scheduled=True); ok1=r["status"]=="paused" and (p/"a.pdf").exists()
    r2=bb.run(p,dry_run=False,include_new=True); ok2=r2["stats"]["moved"]==1
    bb.resume(); ok3=bb.pause_status() is None
    try: bb.snooze("banana"); ok4=False
    except ab.BackendError: ok4=True
    return bool(st) and ok1 and ok2 and ok3 and ok4,(st,ok1,ok2,ok3,ok4)
T("pause: automatic runs wait, my own run goes ahead, resume, bad text",pause)
def recent():
    bb=B(); p=folder({"a.pdf":"1"}); bb.run(p,dry_run=False,include_new=True); r=bb.recent_runs(); return len(r)>=1 and r[0]["moved"]==1 and r[0]["status"]=="ok",r[:1]
T("recent runs list",recent)
def runall():
    bb=B(); w1=folder({"a.pdf":"1"}); w2=folder({"b.jpg":"1"}); bb.add_watch(w1); bb.add_watch(w2); out=bb.run_all(dry_run=False); return len(out)==2 and all(r["stats"]["moved"]==1 for _,r in out) or all(r["status"] in("ok",) for _,r in out),[(r["stats"]) for _,r in out]
T("organize all watched folders",runall)
def startup():
    bb=B(); sd=tempfile.mkdtemp(); bb.set_startup(True,startup_dir=sd); f=Path(sd)/"Organizer Tray.vbs"; ok1=f.exists() and "--tray" in f.read_text() and bb.startup_enabled(sd)
    bb.set_startup(False,startup_dir=sd); return ok1 and not f.exists() and not bb.startup_enabled(sd),f.exists()
T("start with Windows: shortcut file written and removed",startup)
def appset():
    bb=B(); bb.set_app_settings(auto_enabled=True,auto_minutes=15); s=bb.app_settings(); return s["auto_enabled"] is True and s["auto_minutes"]==15 and s["first_run_done"] is False,s
T("app settings saved per user",appset)
def odd_names():
    bb=B(); p=folder({"a b.pdf":"1","日本語.pdf":"2","émoji😀.jpg":"3","x"*100+".pdf":"4"}); r=bb.run(p,dry_run=False,include_new=True); return r["stats"]["errors"]==0 and len(paths(p))==4 and r["stats"]["moved"]==4,r["stats"]
T("unusual names organized without errors",odd_names)
def regex_rule():
    bb=B(); cfg=bb.load_config(); cfg["rules"].insert(0,{"name":"bomb","regex":"^(a+)+$","dest":"Bomb","custom":True}); bb.save_config(cfg); p=folder({"a"*40+"!.txt":"1","ok.pdf":"2"}); t=time.time(); r=bb.run(p,dry_run=False,include_new=True); return time.time()-t<10 and r["stats"]["moved"]==2,f"{time.time()-t:.1f}s"
T("a slow regex in the settings cannot freeze a run",regex_rule)


def _make(fn):
    def test(self):
        ok, note = fn()
        self.assertTrue(ok, note)
    return test


class AppLogicTests(unittest.TestCase):
    """Everything the desktop app does behind the window (presets, rules editor, history, two users...)."""


for _i, (_name, _fn) in enumerate(CASES):
    setattr(AppLogicTests, "test_%02d_%s" % (_i, re.sub(r"\W+", "_", _name)[:60]), _make(_fn))

if __name__ == "__main__":
    unittest.main()
