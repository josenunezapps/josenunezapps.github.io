"""Public BountyBoard API integration; discover ONLY, do not place bids."""
import datetime,json,re,urllib.request
from pathlib import Path
URL="https://www.bountyboard.work/api/bounties?status=OPEN&limit=100"
CURRENCIES={"USD","EUR","PLN","CZK","HUF"}
def normalize(data):
    if not isinstance(data,dict) or not isinstance(data.get("bounties"),list):
        raise ValueError("BountyBoard: formato invalido")
    entries=[];seen=set()
    for b in data["bounties"][:100]:
        if not isinstance(b,dict) or b.get("status")!="OPEN":continue
        ident=str(b.get("id") or "")
        money=b.get("reward")
        cur=str(b.get("currency") or "").upper()
        if not ident or not re.fullmatch(r"[a-zA-Z0-9_-]{8,90}",ident) or ident in seen:continue
        if cur not in CURRENCIES or isinstance(money,bool) or not isinstance(money,int) or money<=0:continue
        seen.add(ident)
        agents=b.get("allowAgents") is True
        category=str(b.get("category") or "")
        code_fit=("Development" in category or "Tech" in category)
        count=b.get("_count") or {}
        claim_count=count.get("claims") if isinstance(count,dict) else None
        slots=b.get("maxHunters")
        remaining_slots=isinstance(slots,int) and isinstance(claim_count,int) and claim_count<slots
        entries.append({"id":"bountyboard:"+ident,"title":str(b.get("title") or "")[:180],
            "source":"BountyBoard","source_listing":"https://www.bountyboard.work/bounties",
            "reward_listed":money/100,"currency":cur,
            "category":category[:70],"status":"OPEN","allow_agents":agents,
            "code_fit":code_fit,"claims":claim_count,"max_hunters":slots,
            "eligible_for_agent":bool(agents and code_fit and remaining_slots),
            "payment_verified":False,
            "reasons":([] if agents else ["El anunciante no admite agentes de IA"])+
              ([] if code_fit else ["La tarea no es de programacion"])+
              ([] if remaining_slots else ["No hay cupos libres confirmados"]),
            "description":str(b.get("description") or "")[:600],
            "seen_at":datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")})
    return entries
def fetch():
    req=urllib.request.Request(URL,headers={"Accept":"application/json","User-Agent":"ZenixAutoWorker/1.2 read-only"})
    with urllib.request.urlopen(req,timeout=18) as r:
        if r.status!=200:raise RuntimeError("HTTP "+str(r.status))
        return normalize(json.loads(r.read(2000000).decode("utf-8")))
def snapshot(path,provider=fetch):
    try:items=provider();status="ok";error=None
    except Exception as exc:
        items=[];status="unavailable";error=type(exc).__name__+": "+str(exc)[:150]
    data={"source":"BountyBoard","source_status":status,"error":error,
          "listed_count":len(items),"agent_eligible_count":sum(bool(i["eligible_for_agent"]) for i in items),
          "opportunities":items,"notice":"No presentar ofertas si allowAgents=false o sin cupos. Pagos no verificados."}
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(".tmp");temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8");temp.replace(path)
    return data
if __name__=="__main__":
    output=Path(__file__).resolve().parent.parent/"data"/"bountyboard.json"
    d=snapshot(output);print("BountyBoard:",d["source_status"],d["listed_count"],"listed",d["agent_eligible_count"],"agent eligible")
