"""Human review state machine. No external applications, PRs or deliveries."""
import argparse, datetime, hashlib, json, re
from pathlib import Path
QUEUE=Path(__file__).resolve().parent.parent/"data"/"reviews.json"
ISSUE=re.compile(r"^https://github\.com/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+/issues/[0-9]+$")
SHA=re.compile(r"^[0-9a-f]{64}$")
STEPS={"proposal_ready":"approve_apply","approved_to_apply":"mark_applied",
       "applied":"ready_delivery","ready_for_delivery":"approve_delivery",
       "approved_to_deliver":"mark_delivered"}
NEXT={"approve_apply":"approved_to_apply","mark_applied":"applied",
      "ready_delivery":"ready_for_delivery","approve_delivery":"approved_to_deliver",
      "mark_delivered":"delivered"}
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")
def identifier(url):return hashlib.sha256(url.encode()).hexdigest()[:16]
def read(path=QUEUE):
    try:
        data=json.loads(Path(path).read_text(encoding="utf-8"))
        return data if isinstance(data,dict) else {}
    except (OSError,ValueError):return {}
def save(data,path=QUEUE):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(".tmp");tmp.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding="utf-8");tmp.replace(path)
def prepare(url,title,source="unverified",path=QUEUE):
    if not ISSUE.fullmatch(url):raise ValueError("Solo URLs publicas de GitHub issues")
    if not isinstance(title,str) or not title.strip():raise ValueError("Titulo obligatorio")
    data=read(path);ident=identifier(url)
    if ident in data:return data[ident]
    proposal=("Hola, vi la tarea "+title.strip()[:160]+".\n\n"
        "Antes de comprometerme, quisiera confirmar disponibilidad de recompensa, requisitos de aceptacion, "
        "plazos, elegibilidad para Argentina y reglas de asistencia con IA.\n\n"
        "Puedo compartir una propuesta tecnica y pruebas verificables si esas condiciones se confirman.")
    row={"id":ident,"url":url,"title":title[:180],"source":source,"payment_verified":False,
        "status":"proposal_ready","proposal":proposal,
        "proposal_sha256":hashlib.sha256(proposal.encode()).hexdigest(),
        "delivery_sha256":None,"history":[{"when":now(),"action":"prepare","actor":"agent"}],
        "disclaimer":"Sin pago confirmado, sin postular ni enviar entregables"}
    data[ident]=row;save(data,path);return row
def advance(url,action,actor,sha256=None,evidence=None,path=QUEUE):
    data=read(path);row=data.get(identifier(url))
    if not row:raise ValueError("Primero preparar trabajo")
    state=row["status"]
    if STEPS.get(state)!=action:raise ValueError("Transicion no permitida: "+state+" -> "+action)
    if action in ("approve_apply","approve_delivery") and actor!="josenunezapps":
        raise PermissionError("La aprobacion requiere al propietario GitHub")
    if action=="ready_delivery":
        if not isinstance(sha256,str) or not SHA.fullmatch(sha256):
            raise ValueError("Hace falta SHA256 del artefacto para revision")
        row["delivery_sha256"]=sha256
    if action=="approve_delivery" and not row.get("delivery_sha256"):
        raise ValueError("No hay artefacto para entregar")
    if action in ("mark_applied","mark_delivered"):
        if not isinstance(evidence,str) or not ISSUE.fullmatch(evidence):
            raise ValueError("Se requiere evidencia publica de la accion manual")
    row["status"]=NEXT[action]
    row["history"].append({"when":now(),"action":action,"actor":actor,
                          "sha256":sha256,"evidence":evidence})
    save(data,path);return row
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--prepare-url");p.add_argument("--title")
    p.add_argument("--action",choices=list(NEXT));p.add_argument("--url")
    p.add_argument("--actor",default="");p.add_argument("--sha256");p.add_argument("--evidence")
    a=p.parse_args()
    if a.prepare_url:result=prepare(a.prepare_url,a.title or "Issue a evaluar")
    elif a.url and a.action:result=advance(a.url,a.action,a.actor,a.sha256,a.evidence)
    else:p.error("Indicar --prepare-url o --action con --url")
    print(json.dumps({"url":result["url"],"status":result["status"],"outbound_actions":0}))
