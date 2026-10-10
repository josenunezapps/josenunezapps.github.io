"""Self-hosted discovery and candidate preparation. Never sends bids or work."""
import argparse,datetime as dt,json,os,shutil,time
from pathlib import Path
from marketplace import snapshot as scan_algora
from bountyboard import snapshot as scan_bountyboard
from reviews import prepare
DATA=Path(__file__).resolve().parent.parent/"data"
def triage(algora,board):
    candidates=[]
    if algora.get("source_status")=="ok":
        for b in algora.get("opportunities",[]):
            if not b.get("url") or not b.get("reward_usd_listed"):continue
            candidates.append({"id":b["id"],"source":"Algora","url":b["url"],
                "title":b["title"],"reward":b["reward_usd_listed"],"currency":"USD",
                "score":min(90,40+int(b["reward_usd_listed"]/25)+(15 if b.get("sponsor_match") else 0)),
                "payment_verified":False,"agent_allowed":"unconfirmed",
                "next":"Check open issue, award conditions and payment eligibility for Argentina"})
    if board.get("source_status")=="ok":
        for b in board.get("opportunities",[]):
            if not b.get("eligible_for_agent"):continue
            candidates.append({"id":b["id"],"source":"BountyBoard",
                "url":b["source_listing"],"title":b["title"],"reward":b["reward_listed"],
                "currency":b["currency"],"score":55,"payment_verified":False,"agent_allowed":True,
                "next":"Check Stripe payout eligibility, then request approval to bid"})
    return sorted(candidates,key=lambda x:x["score"],reverse=True)
def run_once(refresh=True,attempt_code=False):
    DATA.mkdir(parents=True,exist_ok=True)
    algora=scan_algora(DATA/"bounties.json") if refresh else json.loads((DATA/"bounties.json").read_text())
    board=scan_bountyboard(DATA/"bountyboard.json") if refresh else json.loads((DATA/"bountyboard.json").read_text())
    candidates=triage(algora,board)
    for b in candidates:
        if b["source"]=="Algora":prepare(b["url"],b["title"],source="Algora")
    result={"generated_at":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "count":len(candidates),"candidates":candidates,"applied_count":0,"delivered_count":0,
        "note":"Sin postulaciones ni entregas automaticas. Requiere aprobacion humana."}
    (DATA/"agent_queue.json").write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding="utf-8")
    if attempt_code and candidates:
        selected=next((x for x in candidates if x["source"]=="Algora"),None)
        if selected:
            if not (os.environ.get("OPENROUTER_API_KEY") and shutil.which("docker")):
                raise RuntimeError("Se necesita clave de IA gratis y Docker para intentar codigo")
            from agent import work
            work(selected["url"])
    return result
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--once",action="store_true");p.add_argument("--loop",action="store_true")
    p.add_argument("--hours",type=float,default=6);p.add_argument("--attempt-code",action="store_true")
    p.add_argument("--self-hosted",action="store_true")
    a=p.parse_args()
    if not (a.once or a.loop):p.error("Usar --once o --loop")
    if a.loop and not a.self_hosted:p.error("El modo continuo requiere --self-hosted (no GitHub Actions)")
    if a.loop and not 1<=a.hours<=168:p.error("Intervalo de 1 a 168 horas")
    while True:
        result=run_once(attempt_code=a.attempt_code)
        print("AutoWorker:",result["count"],"candidatos; sin envios externos",flush=True)
        if not a.loop:break
        time.sleep(a.hours*3600)
if __name__=="__main__":main()
