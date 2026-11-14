s=open("/home/claude/t/big.py").read().split("# ---------- SIMPLE ----------")[0]; exec(s)
import random
R3=[]; CT={}
def rec(pri,desc,ok,note=""):
    CT[pri]=CT.get(pri,0)+1; id=f"{pri}3-{CT[pri]:03d}"; R3.append((pri,id,desc,ok,str(note)[:90]))
    if ok is not True: print(pri,id,"FAIL" if ok is False else ok,desc[:48],"|",str(note)[:80],flush=True)
def TT(pri,desc,fn):
    try: ok,note=fn()
    except Exception as e: ok,note="ERR",repr(e)[:80]
    rec(pri,desc,ok,note)
def cnt(p): return sum(1 for d,ds,fs in os.walk(p) for x in fs)
def ago(p,days): t=time.time()-days*86400; os.utime(p,(t,t))
def errs0(o): return " 0 errors" in o and "Traceback" not in o
def save(name):
    json.dump(R3,open(f"/tmp/results_{name}.json","w")); 
    for l in "SMH":
        rs=[r for r in R3 if r[0]==l]
        if rs: print("TOTAL",l,sum(1 for r in rs if r[3] is True),"/",len(rs))
