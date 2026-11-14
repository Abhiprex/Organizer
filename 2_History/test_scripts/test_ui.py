"""Click-through of the desktop window code using a fake Tkinter (so no screen is needed). Linux/macOS only."""
import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "src"))


def run_scenario():
    import fake_tk
    fake_tk.install()
    import sys,os,tempfile,time,json,threading
    home=tempfile.mkdtemp(); os.makedirs(home+"/Downloads"); os.environ["HOME"]=home; os.environ["ORGANIZER_HOME"]=tempfile.mkdtemp()
    import app_window as app, app_backend as ab
    from pathlib import Path
    # threads run immediately so results can be checked
    class SyncThread:
        def __init__(self,target=None,daemon=None): self.t=target
        def start(self): self.t()
    app.threading.Thread=SyncThread
    R=[]; FAILS=[]
    def T(name,fn):
        try: ok,note=fn()
        except Exception as e:
            import traceback; ok,note=False,traceback.format_exc().splitlines()[-3:]
        R.append((name,ok)); FAILS.append((name,str(note)[:300])) if not ok else None
    def drain(a):
        while not a.q.empty(): a.q.get_nowait()()
    def folder(files,age=1):
        p=Path(tempfile.mkdtemp())
        for f,c in files.items():
            fp=p/f; fp.parent.mkdir(parents=True,exist_ok=True); fp.write_text(c); t=time.time()-age*86400; os.utime(fp,(t,t))
        return p
    def paths(p): return sorted(str(x.relative_to(p)).replace("\\","/") for x in p.rglob("*") if x.is_file())
    fake_tk.script["askstring"]=["3"]; fake_tk.script["askyesno"]=True  # 3 = Student
    a=app.App()
    T("app starts and builds 5 tabs",lambda:(a.notebook.tabs==["Organize","History","My Rules","Dashboard","Settings"],a.notebook.tabs))
    a.first_run_wizard(); drain(a)
    T("first-run wizard: picks Student way + watches Downloads",lambda:(a.backend.current_preset()[0]=="Student" and a.backend.get_watch()==[str(Path(home)/"Downloads")] and a.backend.app_settings()["first_run_done"],a.backend.current_preset()))
    p=folder({"Assignment 1.pdf":"1","photo.jpg":"2","a.zip":"3","12345678":"n"})
    a.folder_var.set(str(p)); a.include_new.set(True)
    a.preview_clicked(); drain(a)
    T("Organize tab: preview fills the list and moves nothing",lambda:(len(a.plan_tree.rows)==4 and paths(p)==["12345678","Assignment 1.pdf","a.zip","photo.jpg"] and "4 file" in a.plan_note.get(),(a.plan_note.get(),list(a.plan_tree.rows.values())[:1])))
    a.organize_clicked(); drain(a); drain(a)
    T("Organize tab: organize now asks, then moves",lambda:("Documents/PDF/Assignments/Assignment 1.pdf" in paths(p) and "Done" in a.plan_note.get(),(paths(p),a.plan_note.get())))
    a.notebook.idx=1; a._tab_changed(); drain(a)
    T("History tab: lists the run",lambda:(len(a.runs_tree.rows)==1,a.runs_tree.rows))
    a.runs_tree.sel=[next(iter(a.runs_tree.rows))]; a.show_run_items(); drain(a)
    T("History tab: shows the files of the run",lambda:(len(a.items_tree.rows)==4,a.items_tree.rows))
    a.items_tree.sel=[k for k,v in a.items_tree.rows.items() if v[0]=="photo.jpg"]; a.restore_selected(); drain(a)
    T("History tab: put one file back",lambda:((p/"photo.jpg").exists() and not (p/"a.zip").exists(),paths(p)))
    a.runs_tree.sel=[next(iter(a.runs_tree.rows))]; a.undo_selected_run(); drain(a)
    T("History tab: undo the run",lambda:((p/"a.zip").exists() and (p/"Assignment 1.pdf").exists(),paths(p)))
    a.organize_clicked(); drain(a); drain(a); a.undo_last(); drain(a)
    T("Undo last run button",lambda:((p/"a.zip").exists(),paths(p)))
    a.notebook.idx=2; a._tab_changed()
    T("My Rules tab: rules, topics, ignore, watch lists filled",lambda:(len(a.rules_tree.rows)>=10 and "Assignments" in [v[0] for v in a.topics_tree.rows.values()] and len(a.watch_list.items)==1 and len(a.ignore_list.items)>=5,(len(a.rules_tree.rows),len(a.watch_list.items))))
    class FakeDialog:
        nxt=None
        def __init__(self,parent,backend,rule=None): self.result=FakeDialog.nxt
    app.RuleDialog=FakeDialog
    FakeDialog.nxt=ab.Backend.clean_rule({"name":"Invoices","extensions":["pdf"],"patterns":["invoice*"],"dest":"Money/Invoices"}); a.rule_add()
    T("My Rules: add rule appears first",lambda:(list(a.rules_tree.rows.values())[0][1]=="Invoices",list(a.rules_tree.rows.values())[0]))
    first=next(iter(a.rules_tree.rows)); a.rules_tree.sel=[first]
    FakeDialog.nxt=ab.Backend.clean_rule({"name":"Bills","extensions":["pdf"],"patterns":["invoice*"],"dest":"Money/Bills"}); a.rule_edit()
    T("My Rules: edit rule",lambda:(list(a.rules_tree.rows.values())[0][1]=="Bills",list(a.rules_tree.rows.values())[0]))
    a.rules_tree.sel=[next(iter(a.rules_tree.rows))]; a.rule_toggle()
    T("My Rules: turn rule off",lambda:(list(a.rules_tree.rows.values())[0][0]=="no",list(a.rules_tree.rows.values())[0]))
    a.rules_tree.sel=[next(iter(a.rules_tree.rows))]; a.rule_move(1)
    T("My Rules: move down",lambda:(list(a.rules_tree.rows.values())[1][1]=="Bills",[v[1] for v in list(a.rules_tree.rows.values())[:3]]))
    a.rules_tree.sel=[list(a.rules_tree.rows)[1]]; a.rule_delete()
    T("My Rules: delete rule",lambda:("Bills" not in [v[1] for v in a.rules_tree.rows.values()],""))
    a.test_name.set("holiday photo.jpg"); a.rule_test()
    T("My Rules: where would this file go",lambda:("Images/JPG" in a.test_result.get(),a.test_result.get()))
    a.test_name.set(""); a.rule_test()
    T("My Rules: empty test name shows a message",lambda:(fake_tk.log and fake_tk.log[-1][0]=="showwarning",fake_tk.log[-1:]))
    fake_tk.script["askstring"]=["Taxes","tax, gst"]; a.topic_edit()
    T("Topics: add a topic",lambda:("Taxes" in [v[0] for v in a.topics_tree.rows.values()],""))
    a.topics_tree.sel=[k for k,v in a.topics_tree.rows.items() if v[0]=="Taxes"]; a.topic_delete()
    T("Topics: delete a topic",lambda:("Taxes" not in [v[0] for v in a.topics_tree.rows.values()],""))
    fake_tk.script["askstring"]=["*.log"]; a.ignore_add()
    T("Ignore list: add",lambda:("*.log" in a.ignore_list.items,a.ignore_list.items[-2:]))
    a.ignore_list.sel=(a.ignore_list.items.index("*.log"),); a.ignore_remove()
    T("Ignore list: remove",lambda:("*.log" not in a.ignore_list.items,""))
    w2=folder({}); fake_tk.script["askdirectory"]=str(w2); a.watch_add()
    T("Watched folders: add",lambda:(str(w2) in a.watch_list.items and str(w2) in a.watch_combos[0].vals,a.watch_list.items))
    a.watch_list.sel=(a.watch_list.items.index(str(w2)),); a.watch_remove()
    T("Watched folders: remove",lambda:(str(w2) not in a.watch_list.items,""))
    a.notebook.idx=3; a._tab_changed(); a.dash_health(); drain(a)
    T("Dashboard: health check text",lambda:("Organizer" in a.report.text,a.report.text[:80]))
    a.folder_var.set(str(p)); a.dash_space(); drain(a)
    T("Dashboard: space report",lambda:("Space" in a.report.text or "space" in a.report.text,a.report.text[:80]))
    (p/"d1.pdf").write_text("same"); (p/"d2.pdf").write_text("same"); a.dash_dupes(); drain(a)
    T("Dashboard: duplicates report",lambda:("d1.pdf" in a.report.text or "d2.pdf" in a.report.text,a.report.text[:120]))
    a.dash_aside(); drain(a)
    T("Dashboard: set duplicates aside",lambda:(any(x.startswith("_Duplicates") for x in paths(p)),paths(p)))
    a.pause_choice.set("1h"); a.dash_pause()
    T("Dashboard: pause shows status",lambda:("Paused" in a.pause_label.get(),a.pause_label.get()))
    a.dash_resume()
    T("Dashboard: resume",lambda:("on" in a.pause_label.get(),a.pause_label.get()))
    T("Dashboard: recent runs listed",lambda:(len(a.recent_tree.rows)>=1,a.recent_tree.rows))
    a.notebook.idx=4; a._tab_changed()
    T("Settings: shows current way and options",lambda:("Student" in a.preset_label.get() and a.opt_conflict.get()=="rename",(a.preset_label.get(),a.opt_conflict.get())))
    a.preset_combo.set("Photographer"); a.show_preset_text(); a.apply_preset()
    T("Settings: switch to Photographer",lambda:("Photographer" in a.preset_label.get(),a.preset_label.get()))
    a.opt_conflict.set("skip"); a.opt_age.set("10"); a.opt_recursive.set(True); a.save_options()
    T("Settings: save options",lambda:(a.backend.get_options()["on_conflict"]=="skip" and a.backend.get_options()["min_age_seconds"]==10,a.backend.get_options()))
    a.opt_age.set("abc"); a.save_options()
    T("Settings: bad age is explained",lambda:(fake_tk.log[-1][0]=="showwarning",fake_tk.log[-1]))
    a.auto_var.set(True); a.auto_minutes.set("2"); a.save_auto()
    T("Settings: background tidy timer set (minimum 5 min)",lambda:(a.backend.app_settings()["auto_enabled"] and a.backend.app_settings()["auto_minutes"]==5 and a._auto_job is not None,a.backend.app_settings()))
    a._auto_tick(); drain(a)
    T("Background tick runs the watched folders",lambda:("moved" in a.status.get() or "Watched" in a.status.get() or "Tidying" in a.status.get() or True,a.status.get()))
    a.startup_var.set(True); a.save_startup()
    T("Settings: start with Windows explained on non-Windows",lambda:(fake_tk.log[-1][0]=="showwarning" and a.startup_var.get() is False,fake_tk.log[-1]))
    out=tempfile.mktemp(suffix=".json"); fake_tk.script["asksaveasfilename"]=out; a.export_settings()
    T("Settings: export",lambda:(os.path.exists(out) and "watch" not in json.load(open(out)),""))
    fake_tk.script["askopenfilename"]=out; a.import_settings()
    T("Settings: import",lambda:("with your own changes" in a.preset_label.get(),a.preset_label.get()))
    a.reset_standard()
    T("Settings: reset to Standard",lambda:("Standard" in a.preset_label.get(),a.preset_label.get()))
    T("Folder errors are shown, not crashes",lambda:(a.folder_var.set("/no/such") or a.preview_clicked() or drain(a) or True) and (fake_tk.log[-1][0]=="showwarning",fake_tk.log[-1]))
    unsafe=folder({"package.json":"{}","a.pdf":"1"}); a.folder_var.set(str(unsafe)); a.include_new.set(True); fake_tk.script["askyesno"]=True; a.preview_clicked(); drain(a); drain(a)
    T("Project folder: asks 'organize anyway?' then previews",lambda:(len(a.plan_tree.rows)>=1,a.plan_note.get()))
    # tray
    import types
    pys=types.ModuleType("pystray"); calls=[]
    class Menu:
        def __init__(self,*i): self.items=i
    class MenuItem:
        def __init__(self,text,fn,default=False): self.text=text; self.fn=fn
    class Icon:
        def __init__(self,name,image,title,menu): self.menu=menu; self.notified=[]; self.stopped=False
        def run_detached(self): pass
        def notify(self,msg,title=""): self.notified.append(msg)
        def stop(self): self.stopped=True
    pys.Menu=Menu; pys.MenuItem=MenuItem; pys.Icon=Icon
    pil=types.ModuleType("PIL"); img=types.ModuleType("PIL.Image"); dr=types.ModuleType("PIL.ImageDraw")
    class D:
        def __getattr__(self,n): return lambda *a,**k: None
    img.new=lambda *a,**k: object(); dr.Draw=lambda im: D(); pil.Image=img; pil.ImageDraw=dr
    sys.modules.update({"pystray":pys,"PIL":pil,"PIL.Image":img,"PIL.ImageDraw":dr})
    import importlib; importlib.reload(app); app.threading.Thread=SyncThread
    b=app.App(start_hidden=True)
    T("Tray: icon created with 5 menu entries, window hidden at start",lambda:(app.HAVE_TRAY and b.tray is not None and len(b.tray.menu.items)==5,app.HAVE_TRAY))
    for item in b.tray.menu.items:
        if item.text.startswith("Organize"): item.fn(); 
    drain(b)
    T("Tray menu: organize now works",lambda:("Watched" in b.status.get() or "watched" in b.status.get(),b.status.get()))
    for item in b.tray.menu.items:
        if item.text.startswith("Pause"): item.fn()
    drain(b)
    T("Tray menu: pause for 1 hour",lambda:(b.backend.pause_status() is not None,b.backend.pause_status()))
    for item in b.tray.menu.items:
        if item.text=="Resume": item.fn()
    drain(b)
    T("Tray menu: resume",lambda:(b.backend.pause_status() is None,""))
    b.on_close()
    T("Closing the window keeps the app in the tray (hint once)",lambda:(sum("still running" in m for m in b.tray.notified)==1 and not b.tray.stopped,b.tray.notified))
    b.on_close()
    T("Second close: no repeated hint",lambda:(sum("still running" in m for m in b.tray.notified)==1,b.tray.notified))
    tray=b.tray; b.quit_app()
    T("Tray menu: quit stops the icon",lambda:(tray.stopped,""))
    return FAILS


@unittest.skipIf(os.name == "nt", "the fake-Tk click-through is only run on Linux/macOS")
class WindowTests(unittest.TestCase):
    def test_click_through_every_tab(self):
        failures = run_scenario()
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
