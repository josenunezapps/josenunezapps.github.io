"""Read-only Algora bounty discovery. Reward listing != guaranteed payment."""
from __future__ import annotations
import datetime as dt
import json, re, urllib.parse, urllib.request
from pathlib import Path
ISSUE=re.compile(r"^https://github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)/issues/([0-9]+)$")
ENDPOINT="https://console.algora.io/api/trpc/bounty.list"
def now():return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
def normalize(payload, seen_at=None):
    if not isinstance(payload,list) or not payload:raise ValueError("Algora: formato incorrecto")
    try:items=payload[0]["result"]["data"]["json"]["items"]
    except (KeyError,TypeError,IndexError) as e:raise ValueError("Algora: lista no disponible") from e
    if not isinstance(items,list):raise ValueError("Algora: respuesta invalida")
    result=[];used=set()
    for item in items[:100]:
        if not isinstance(item,dict):continue
        task=item.get("task") or {};org=item.get("org") or {};reward=item.get("reward") or {}
        if not all(isinstance(x,dict) for x in (task,org,reward)):continue
        url=task.get("url")
        match=ISSUE.fullmatch(url) if isinstance(url,str) else None
        cents=reward.get("amount")
        if not match or isinstance(cents,bool) or not isinstance(cents,(int,float)) or not 0<cents<1e8:continue
        ident=str(item.get("id") or "")
        if not ident or ident in used:continue
        used.add(ident)
        orgname=str(org.get("handle") or "")
        result.append({"id":"algora:"+ident,"title":str(task.get("title") or "Recompensa publicada")[:180],
            "url":url,"source":"Algora","org":str(org.get("display_name") or orgname)[:80],
            "source_listing":"https://algora.io/"+urllib.parse.quote(orgname)+"/bounties",
            "reward_usd_listed":round(cents/100,2),
            "payment_verified":False,"reward_status":"listed_unverified",
            "sponsor_match":bool(org.get("github_handle") and match.group(1).lower()==str(org["github_handle"]).lower()),
            "seen_at":seen_at or now(),
            "screening":"Confirmar bounty abierto, plazo, reglas de IA, pais, exclusividad y pago."})
    return result
def fetch_open(timeout=18):
    inp=json.dumps({"limit":100,"status":"open"},separators=(",",":"))
    url=ENDPOINT+"?"+urllib.parse.urlencode({"input":inp})
    req=urllib.request.Request(url,headers={"User-Agent":"Zenix-AutoWorker/1.2 read-only","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=timeout) as response:
        if response.status!=200:raise RuntimeError("HTTP "+str(response.status))
        return normalize(json.loads(response.read(2000000).decode("utf-8")))
def snapshot(path,provider=fetch_open):
    try:entries=provider();status="ok";error=None
    except Exception as exc:
        entries=[];status="unavailable";error=type(exc).__name__+": "+str(exc)[:150]
    data={"generated_at":now(),"source":"Algora open bounties","source_status":status,
          "error":error,"listed_count":len(entries),"opportunities":entries,
          "notice":"Recompensas publicadas; pago/eligibilidad NO verificados. Sin envios a terceros."}
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(path)
    return data
if __name__=="__main__":
    path=Path(__file__).resolve().parent.parent/"data"/"bounties.json"
    result=snapshot(path)
    print("Algora",result["source_status"],result["listed_count"])
