#!/usr/bin/env python3
"""URF state utility: validated state changes, deterministic selection and
atomic publication for Continuous research. Command reference: UTILITY.md.

Single maintainer, single run. Python 3.10+, standard library only.
Exit codes: 0 ok, 2 validation failure (nothing written), 3 precondition failure.
"""
import argparse
import copy
import datetime as dt
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys

CORE_KEYS = ["schema_version", "last_run", "baseline", "sources", "items",
             "historical_ids", "pending_leads"]
RUN_REPORT = "@run-report"
STAGING = os.path.join(".urf", "run")
PRESERVED = os.path.join(".urf", "preserved")
OPS_RE = re.compile(r"<!-- urf-ops\n(.*?)\n-->", re.S)
REPAIR_OPS = {"source.set_coverage", "baseline.set_window", "item.add_alias", "lead.resolve"}


class Fail(Exception):
    def __init__(self, code, message, **extra):
        super().__init__(message)
        self.code, self.message, self.extra = code, message, extra


# ---------------------------------------------------------------- I/O helpers

def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sha_file(path):
    try:
        with open(path, "rb") as f:
            return sha(f.read())
    except FileNotFoundError:
        return None


def atomic_write(path, text):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".urf-tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def detect_format(raw):
    """Keep the existing file's layout (indentation, escaping, one-line list
    entries) so publication diffs stay small."""
    m = re.search(r"\n( +)\S", raw)
    ind = len(m.group(1)) if m else 2
    asc = "\\u" in raw and all(ord(c) < 128 for c in raw)
    compact = [k for k, v in json.loads(raw).items() if isinstance(v, list) and v
               and "\n" + " " * 2 * ind + json.dumps(v[0], ensure_ascii=asc) in raw]
    return {"indent": ind, "ascii": asc, "compact": compact}


def dump_state(state, fmt):
    ind, asc = fmt["indent"], fmt["ascii"]
    parts = []
    for k, v in state.items():
        if k in fmt.get("compact", []) and isinstance(v, list) and v:
            rows = ",\n".join(" " * 2 * ind + json.dumps(e, ensure_ascii=asc) for e in v)
            val = "[\n" + rows + "\n" + " " * ind + "]"
        else:
            val = json.dumps(v, indent=ind, ensure_ascii=asc).replace("\n", "\n" + " " * ind)
        parts.append(" " * ind + json.dumps(k, ensure_ascii=asc) + ": " + val)
    return "{\n" + ",\n".join(parts) + "\n}\n"


def git(root, *args):
    try:
        r = subprocess.run(["git", "-C", root] + list(args), capture_output=True)
    except FileNotFoundError:
        return None
    return r.stdout if r.returncode == 0 else None


def head_sha(root, rel):
    data = git(root, "show", "HEAD:" + rel.replace(os.sep, "/"))
    return sha(data) if data is not None else None


# ---------------------------------------------------------------- dates

def D(s):
    return dt.date.fromisoformat(s)


def period(a, b):
    return f"{a.isoformat()}..{b.isoformat()}"


def months(start, end):
    out, s = [], start
    while s <= end:
        nxt = (s.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
        e = min(end, nxt - dt.timedelta(days=1))
        out.append(period(s, e))
        s = e + dt.timedelta(days=1)
    return out


def is_date(v):
    try:
        D(v)
        return True
    except (TypeError, ValueError):
        return False


# ---------------------------------------------------------------- identity

class Ident:
    def __init__(self, profile):
        self.p = profile
        self.sk = profile.get("secondary_key")

    def derive(self, name):
        cfg = self.p["id"]
        return cfg["prefix"] + (name.lower() if cfg.get("lowercase") else name)

    def lead_id(self, lead):
        return lead.get("id") or self.derive(lead["name"])

    def index(self, st):
        """kind -> (id -> secondary key, secondary key -> id)."""
        idx = {}
        rows = {
            "item": [(k, v.get(self.sk)) for k, v in st["items"].items()],
            "historical": [(k, v.get(self.sk)) for k, v in st["historical_ids"].items()],
            "rejected": list(st.get("rejected_ids", {}).items()) if self.p.get("rejected_ids") else [],
            "pending": [(self.lead_id(l), l.get(self.sk)) for l in st["pending_leads"]],
        }
        for kind, pairs in rows.items():
            idx[kind] = ({i: s for i, s in pairs}, {s: i for i, s in pairs if s is not None})
        return idx

    @staticmethod
    def match(idx, kind, cid, sk):
        """Secondary key first, then ID. A rejected entry matches by ID only when
        either secondary key is unknown (framework rule); other kinds always do,
        because one ID can never name two entries."""
        ids, sks = idx[kind]
        if sk is not None and sk in sks:
            return sks[sk]
        if cid in ids and (kind != "rejected" or sk is None or ids[cid] is None):
            return cid
        return None


# ---------------------------------------------------------------- validation

def validate(st, P, root, base=None, ctx=None):
    """Return (errors, warnings). ctx is set for staged or repair checks."""
    E, W = [], []
    ctx = ctx or {}
    I = Ident(P)
    extra = set(P.get("top_level", []))
    keys = set(st)
    for k in CORE_KEYS:
        if k not in st:
            E.append(f"missing top-level key {k}")
    for k in keys - set(CORE_KEYS) - extra:
        E.append(f"undeclared top-level key {k}")
    if E:
        return E, W
    if st["schema_version"] != 1:
        E.append("schema_version must be 1")
    lr = st["last_run"]
    if not isinstance(lr, dict) or set(lr) != {"date", "type", "status", "report"}:
        E.append("last_run must have date, type, status, report")
    bl = st["baseline"]
    win = bl.get("window", {})
    if bl.get("status") not in ("not_started", "in_progress", "complete"):
        E.append("baseline.status invalid")
    elif bl["status"] != "not_started" and not (is_date(win.get("from")) and is_date(win.get("to"))):
        E.append("baseline.window must be fixed once the baseline has started")
    pat = re.compile(P["id"]["pattern"])
    # sources and coverage (C1)
    for m, s in st["sources"].items():
        if not is_date(s.get("from")):
            E.append(f"sources.{m}.from invalid")
            continue
        ct = s.get("covered_through")
        if ct is not None:
            if not is_date(ct):
                E.append(f"sources.{m}.covered_through invalid")
                continue
            if D(ct) < D(s["from"]) - dt.timedelta(days=1):
                E.append(f"sources.{m}.covered_through before from")
            mode = P["methods"].get(m, {}).get("baseline")
            if ctx.get("run_date"):
                limit = ctx["run_date"] if mode == "recency" else ctx["lcd"]
                if D(ct) > D(limit):
                    E.append(f"sources.{m}.covered_through {ct} beyond {limit} (C1)")
        if s.get("last_status") not in (None, "complete", "partial", "failed"):
            E.append(f"sources.{m}.last_status invalid")
        cp = s.get("checkpoint")
        if cp is not None:
            if set(cp) != {"period", "config", "done", "report"} or not isinstance(cp["done"], list):
                E.append(f"sources.{m}.checkpoint malformed")
            elif cp["report"] != RUN_REPORT and not os.path.exists(os.path.join(root, cp["report"])):
                E.append(f"sources.{m}.checkpoint report missing: {cp['report']}")
        if base and not ctx.get("repair"):
            b = base["sources"].get(m)
            if b and b.get("covered_through") and (ct is None or D(ct) < D(b["covered_through"])):
                E.append(f"sources.{m}.covered_through decreased (C1)")
    if bl.get("status") == "complete":
        for m, s in st["sources"].items():
            if s.get("from") == win.get("from") and (s.get("covered_through") is None or D(s["covered_through"]) < D(win["to"])):
                E.append(f"baseline complete but {m} not covered through window.to")
    # items
    req = P.get("item_required", [])
    for k, v in st["items"].items():
        if not pat.match(k):
            E.append(f"item key {k} does not match the ID pattern")
        if v.get("status") != "active":
            E.append(f"item {k}: status must be active")
        miss = [f for f in req + ["first_seen", "last_seen", "last_verified", "fingerprint", "report"] if f not in v]
        if miss:
            E.append(f"item {k}: missing {', '.join(miss)}")
        if v.get("relevance") not in P.get("item_relevance", [v.get("relevance")]):
            E.append(f"item {k}: relevance {v.get('relevance')} not allowed")
        rep = v.get("report")
        if rep and rep != RUN_REPORT and not os.path.exists(os.path.join(root, rep)):
            E.append(f"item {k}: report missing {rep}")
        name = v.get("name")
        if name and I.derive(name) != k:
            aliases = [I.derive(a) for a in v.get("aliases", [])]
            if k not in aliases:
                W.append(f"item {k}: current name {name} differs from the ID and the old name is not in aliases")
    keep = P.get("historical_keep", [])
    for k, v in st["historical_ids"].items():
        if not pat.match(k):
            E.append(f"historical key {k} does not match the ID pattern")
        miss = [f for f in ["inactive_since", "fingerprint", "report"] + keep if f not in v]
        if miss:
            E.append(f"historical {k}: missing {', '.join(miss)}")
    if P.get("rejected_ids"):
        for k in st.get("rejected_ids", {}):
            if not pat.match(k):
                E.append(f"rejected key {k} does not match the ID pattern")
    # leads and disjoint identity
    lreq = P.get("lead_required", [])
    seen_ids, seen_sk = set(), set()
    for l in st["pending_leads"]:
        miss = [f for f in lreq if f not in l]
        if miss:
            E.append(f"lead {l.get('name')}: missing {', '.join(miss)}")
            continue
        lid, sk = I.lead_id(l), l.get(I.sk)
        if lid in seen_ids or (sk is not None and sk in seen_sk):
            E.append(f"duplicate pending lead {lid}")
        seen_ids.add(lid)
        if sk is not None:
            seen_sk.add(sk)
    idx = I.index(st)
    for l in st["pending_leads"]:
        lid, sk = I.lead_id(l), l.get(I.sk)
        for kind in ("item", "historical", "rejected"):
            hit = Ident.match(idx, kind, lid, sk)
            if hit:
                E.append(f"pending lead {lid} is also a {kind} entry ({hit})")
    for k in set(st["items"]) & set(st["historical_ids"]):
        E.append(f"{k} is both active and historical")
    owners = {}
    for kind in ("item", "historical", "rejected"):
        for s, i in idx[kind][1].items():
            if s in owners and owners[s] != i:
                E.append(f"secondary key {s} used by {owners[s]} and {i}")
            owners[s] = i
    # continuity against the base state (C2 and history)
    if base:
        for k in base["historical_ids"]:
            if k not in st["historical_ids"] and k not in st["items"]:
                E.append(f"historical entry {k} removed (C2)")
        for k in base["items"]:
            if k not in st["items"] and k not in st["historical_ids"]:
                E.append(f"item {k} removed")
        for k in base.get("rejected_ids", {}):
            if k not in st.get("rejected_ids", {}):
                E.append(f"rejected entry {k} removed")
        bw = base["baseline"].get("window", {})
        if bw.get("from") and bw != win and not ctx.get("repair"):
            E.append("baseline.window changed")
        allowed = set(ctx.get("removed_leads", []))
        now = {I.lead_id(l) for l in st["pending_leads"]}
        for l in base["pending_leads"]:
            lid = I.lead_id(l)
            if lid not in now and lid not in allowed:
                E.append(f"pending lead {lid} removed without an operation")
    if ctx.get("budgets"):
        for k, used in ctx["counters"].items():
            if used > ctx["budgets"].get(k, math.inf):
                E.append(f"{k} budget exceeded: {used} > {ctx['budgets'][k]}")
    return E, W


# ---------------------------------------------------------------- project context

class Project:
    def __init__(self, root, profile_path=None):
        self.root = root
        self.state_path = os.path.join(root, "state.json")
        self.stage = os.path.join(root, STAGING)
        self.P = read_json(profile_path or os.path.join(root, "framework", "state-profile.json"))
        self.I = Ident(self.P)

    def p(self, *parts):
        return os.path.join(self.root, *parts)

    def load_state(self):
        try:
            with open(self.state_path, encoding="utf-8") as f:
                raw = f.read()
            return json.loads(raw), raw
        except (OSError, ValueError) as e:
            raise Fail(3, f"state.json cannot be read or parsed; it was left untouched: {e}")

    def config_sha(self, cfg):
        h = hashlib.sha256(json.dumps(cfg, sort_keys=True).encode())
        files = [self.p("PROJECT.md"), self.p("SOURCES.md")]
        for d, _, fs in os.walk(self.p("framework")):
            files += [os.path.join(d, f) for f in fs if f != ".DS_Store"]
        for f in sorted(files):
            h.update(os.path.relpath(f, self.root).encode())
            h.update((sha_file(f) or "absent").encode())
        return h.hexdigest()

    def has_stage(self):
        return os.path.exists(os.path.join(self.stage, "manifest.json"))

    def manifest(self):
        return read_json(os.path.join(self.stage, "manifest.json"))

    def work(self):
        return read_json(os.path.join(self.stage, "work.json"))

    def save(self, manifest=None, work=None):
        if work is not None:
            atomic_write(os.path.join(self.stage, "work.json"), json.dumps(work, ensure_ascii=False))
        if manifest is not None:
            atomic_write(os.path.join(self.stage, "manifest.json"), json.dumps(manifest, indent=1))

    def preserve(self, label):
        n, dest = 1, None
        while dest is None or os.path.exists(dest):
            dest = self.p(PRESERVED, f"{label}-{n}")
            n += 1
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        os.rename(self.stage, dest)
        return os.path.relpath(dest, self.root)

    def require_stage(self, phase="staged"):
        if not self.has_stage():
            raise Fail(3, "no run in progress; run begin first")
        m = self.manifest()
        if m["phase"] != phase:
            raise Fail(3, f"run is in phase {m['phase']}, expected {phase}")
        return m


# ---------------------------------------------------------------- plan

def make_plan(st, cfg, P, run_date, lcd):
    btype = "incremental" if st["baseline"]["status"] == "complete" else "baseline"
    days = dt.timedelta(days=cfg["baseline_window_days"])
    win = dict(st["baseline"].get("window") or {})
    if not win.get("from"):
        win = {"from": (lcd - days).isoformat(), "to": lcd.isoformat()}
    plan = {"type": btype, "window": win, "methods": {}}
    for m, mc in cfg["methods"].items():
        if m not in P["methods"]:
            raise Fail(3, f"method {m} is not defined in the framework profile")
        mode = P["methods"][m]["baseline"]
        entry = st["sources"].get(m)
        frm = entry["from"] if entry else (win["from"] if btype == "baseline" else (lcd - days).isoformat())
        ct = entry.get("covered_through") if entry else None
        start = D(ct) + dt.timedelta(days=1) if ct else D(frm)
        if mode == "recency":
            periods = [period(run_date, run_date)]
        else:
            end = D(win["to"]) if btype == "baseline" else lcd
            if start > end:
                periods = []
            elif btype == "baseline" and mode == "month":
                periods = months(start, end)
            else:
                periods = [period(start, end)]
        plan["methods"][m] = {"mode": mode, "from": frm, "covered_through": ct,
                              "config": mc["config"], "operations": list(mc["operations"]),
                              "periods": periods, "reusable": []}
    return plan


def report_ops(root, rel):
    """Operations a committed report records, from its urf-ops block; None for legacy reports."""
    try:
        with open(os.path.join(root, rel), encoding="utf-8") as f:
            m = OPS_RE.search(f.read())
    except OSError:
        return None
    return json.loads(m.group(1))["ops"] if m else None


def checkpoint_reuse(project, st, plan):
    """Existing checkpoint semantics: same period and shared config, report present."""
    for m, pm in plan["methods"].items():
        cp = (st["sources"].get(m) or {}).get("checkpoint")
        if not cp or not pm["periods"] or cp["period"] != pm["periods"][0] or cp["config"] != pm["config"]:
            continue
        if not os.path.exists(project.p(cp["report"])):
            continue
        listed = report_ops(project.root, cp["report"])
        for op in cp["done"]:
            if op not in pm["operations"]:
                continue  # removed query: dropped from done
            if listed is None:
                pm["reusable"].append({"op": op, "evidence": cp["report"], "needs_confirmation": True})
                continue
            rec = next((r for r in listed if r["method"] == m and r["period"] == cp["period"] and r["op"] == op), None)
            if rec and rec["status"] == "complete":
                pm["reusable"].append({"op": op, "evidence": cp["report"], "needs_confirmation": False})
            elif rec and rec["status"] == "reused" and os.path.exists(project.p(rec.get("evidence", ""))):
                pm["reusable"].append({"op": op, "evidence": rec["evidence"], "needs_confirmation": False})


# ---------------------------------------------------------------- begin / discard

def cmd_begin(pr, a):
    cfg = read_json(a.config)
    if cfg.get("contract") != "continuous":
        raise Fail(3, "the utility serves Contract: continuous only")
    now = dt.datetime.fromisoformat(a.now.replace("Z", "+00:00")).astimezone(dt.timezone.utc)
    run_date = now.date()
    mode = publication_mode(cfg, run_date)
    lcd = run_date - dt.timedelta(days=1)
    note = preflight(pr, cfg, run_date)
    if note.get("resume"):
        m = pr.manifest()
        return {"resumed": True, "plan": m["plan"], "run_date": m["run_date"], "lcd": m["lcd"],
                "budgets": m["budgets"], "counters": pr.work()["counters"]}
    st, raw = pr.load_state()
    E, W = validate(st, pr.P, pr.root)
    if E:
        raise Fail(3, "published state.json fails validation; repair it before a run", errors=E)
    plan = make_plan(st, cfg, pr.P, run_date, lcd)
    checkpoint_reuse(pr, st, plan)
    budgets = dict(cfg["budgets"])
    if plan["type"] == "baseline" and cfg.get("baseline_budgets"):
        budgets.update(cfg["baseline_budgets"])
    interval = cfg.get("reverify_interval_days", pr.P.get("reverify_interval_days"))
    manifest = {"run_date": run_date.isoformat(), "lcd": lcd.isoformat(), "started_at": now.isoformat(),
                "phase": "staged", "base_sha": sha(raw.encode("utf-8")), "config_sha": pr.config_sha(cfg),
                "format": detect_format(raw), "budgets": budgets, "reverify_interval_days": interval,
                "plan": plan, "targets": None, "status": None, "publication_mode": mode}
    work = {"state": st, "base": st, "ops": [], "seen_ids": [], "seen_sk": [], "log": [], "attempted": [],
            "reverified": [], "counters": {"search": 0, "verify": 0, "reverify": 0}}
    os.makedirs(pr.stage, exist_ok=True)
    pr.save(manifest=manifest, work=work)
    nops = sum(len(pm["operations"]) for pm in plan["methods"].values() if pm["periods"])
    warnings = note.get("warnings", []) + W
    if nops > budgets["search"]:
        warnings.append(f"search budget {budgets['search']} is below one pass of {nops} configured operations; coverage cannot complete in this run")
    return {"resumed": False, "run_date": manifest["run_date"], "lcd": manifest["lcd"], "plan": plan,
            "budgets": budgets, "warnings": warnings, "counts": counts(st, pr.P, run_date, interval)}


def publication_mode(cfg, run_date):
    """automatic: push access is required. manual-supervised: one supervised run the
    maintainer authorizes by its execution date; the maintainer pushes."""
    push, mode = cfg.get("push_available"), cfg.get("publication_mode", "automatic")
    if not isinstance(push, bool):
        raise Fail(3, "push_available must be true or false")
    if mode == "automatic":
        if not push:
            raise Fail(3, "push access unavailable: stop before research; persist no report (common contract section 5)")
    elif mode == "manual-supervised":
        auth = cfg.get("maintainer_authorization")
        if not isinstance(auth, str) or run_date.isoformat() not in auth:
            raise Fail(3, "manual-supervised publication needs maintainer_authorization naming this run's execution date")
    else:
        raise Fail(3, f"unsupported publication_mode {mode!r}")
    return mode


def counts(st, P, run_date, interval):
    due = [k for k, v in st["items"].items() if D(v["last_verified"]) + dt.timedelta(days=interval) <= run_date]
    return {"items": len(st["items"]), "pending_leads": len(st["pending_leads"]),
            "historical": len(st["historical_ids"]), "rejected": len(st.get("rejected_ids", {})),
            "due_reverification": len(due)}


def preflight(pr, cfg, run_date):
    if pr.has_stage():
        m = pr.manifest()
        if m["phase"] == "staged":
            why = []
            if m["run_date"] != run_date.isoformat():
                why.append(f"staged run date {m['run_date']} is not today's UTC date {run_date}")
            if m["base_sha"] != sha_file(pr.state_path):
                why.append("published state.json changed since the run began")
            if m["config_sha"] != pr.config_sha(cfg):
                why.append("project, framework or run configuration changed since the run began")
            if why:
                raise Fail(3, "unfinished run cannot be resumed; staging was left untouched. Inspect .urf/run/, "
                              "or run `urf.py discard` to move it to .urf/preserved/", reasons=why)
            return {"resume": True}
        targets = m["targets"] or {}
        written = all(sha_file(pr.p(t)) == h for t, h in targets.items())
        committed = all(head_sha(pr.root, t) == h for t, h in targets.items())
        if committed:
            return {"warnings": [cleanup(pr, m)]}
        if m["phase"] == "published" and written:
            raise Fail(3, "unfinished publication: commit these files, then begin again", files=sorted(targets))
        raise Fail(3, "publication was interrupted: run `urf.py finish` again to republish from staging")
    dirty = git(pr.root, "status", "--porcelain", "--", "state.json", "reports")
    if dirty:
        raise Fail(3, "uncommitted changes in state.json or reports/ without a run in progress; resolve them first",
                   files=dirty.decode().splitlines())
    return {}


def cleanup(pr, m):
    if m["status"] == "failed":
        return f"failed run preserved for inspection at {pr.preserve(m['run_date'] + '-failed')}"
    try:
        shutil.rmtree(pr.stage)
        return "published run's staging removed"
    except OSError:
        return f"staging could not be deleted; moved to {pr.preserve(m['run_date'])}"


def cmd_discard(pr, a):
    m = pr.manifest() if pr.has_stage() else None
    if not m:
        raise Fail(3, "no staging to discard")
    return {"moved_to": pr.preserve(m["run_date"] + "-discarded")}


# ---------------------------------------------------------------- record

def cmd_record(pr, a):
    m = pr.require_stage()
    w = pr.work()
    rec = read_json(a.file)
    meth, per, op = rec["method"], rec["period"], rec["op"]
    pm = m["plan"]["methods"].get(meth)
    if not pm or per not in pm["periods"] or op not in pm["operations"]:
        raise Fail(2, f"{meth} {per} {op} is not a planned operation")
    done = [o for o in w["ops"] if (o["method"], o["period"], o["op"]) == (meth, per, op) and o["status"] in ("complete", "reused")]
    if done:
        raise Fail(2, "operation already recorded as complete in this run")
    if rec.get("reuse"):
        r = next((x for x in pm["reusable"] if x["op"] == op), None)
        if not r or per != pm["periods"][0]:
            raise Fail(2, "operation is not reusable from the checkpoint")
        if r["needs_confirmation"] and rec.get("confirmed") is not True:
            raise Fail(2, "legacy checkpoint report: confirm that it records this operation as complete (confirmed: true)")
        w["ops"].append({"method": meth, "period": per, "op": op, "status": "reused", "evidence": r["evidence"]})
        pr.save(work=w)
        return {"status": "reused", "evidence": r["evidence"]}
    status, reasons = rec.get("status"), []
    if status not in ("complete", "incomplete", "unattempted"):
        raise Fail(2, "status must be complete, incomplete or unattempted")
    requests = int(rec.get("requests", 0))
    if w["counters"]["search"] + requests > m["budgets"]["search"]:
        raise Fail(2, f"search budget {m['budgets']['search']} would be exceeded; stop discovery")
    if status == "complete":
        for chk in pr.P["methods"][meth].get("completion", []):
            ok, why = check(chk, rec)
            if not ok:
                reasons.append(why)
        if reasons:
            status = "incomplete"
    w["counters"]["search"] += requests
    classes, out = classify(pr, w, rec.get("candidates", []))
    metrics = {k: v for k, v in rec.items() if k not in ("candidates", "method", "period", "op", "status")}
    w["ops"].append({"method": meth, "period": per, "op": op, "status": status, "reasons": reasons, **metrics,
                     "candidates": len(rec.get("candidates", []))})
    pr.save(work=w)
    return {"status": status, "reasons": reasons, "classes": classes, **out,
            "search_used": w["counters"]["search"]}


def check(chk, rec):
    field, op, want = chk
    val = rec.get(field)

    def ref(x):
        if isinstance(x, str) and x.startswith("$"):
            return rec.get(x[1:])
        if isinstance(x, dict) and "min" in x:
            vals = [ref(y) for y in x["min"]]
            return None if None in vals else min(vals)
        return x

    target = ref(want)
    good = val is not None and target is not None and {"==": val == target, ">=": val >= target}[op]
    return good, f"completion check failed: {field} {op} {want} (got {val!r}, expected {target!r})"


def classify(pr, w, cands):
    I, st = pr.I, w["state"]
    idx = I.index(st)
    classes = {k: 0 for k in ("new", "item", "historical", "rejected", "pending", "dup_in_run")}
    out = {"new": [], "changed_items": [], "historical": [], "enrich": []}
    seen_ids, seen_sk = set(w["seen_ids"]), set(w["seen_sk"])
    for c in cands:
        cid = c.get("id") or I.derive(c["name"])
        sk = c.get(I.sk)
        if cid in seen_ids or (sk is not None and sk in seen_sk):
            classes["dup_in_run"] += 1
            continue
        seen_ids.add(cid)
        if sk is not None:
            seen_sk.add(sk)
        kind = next((k for k in ("item", "historical", "rejected", "pending") if Ident.match(idx, k, cid, sk)), "new")
        classes[kind] += 1
        hit = Ident.match(idx, kind, cid, sk) if kind != "new" else None
        if kind == "new":
            out["new"].append(c)
        elif kind == "item":
            fp = st["items"][hit].get("fingerprint", {})
            diff = {f: [fp.get(f), c[f]] for f in pr.P.get("indicators", []) if f in c and f in fp and c[f] != fp[f]}
            other = sk is not None and st["items"][hit].get(I.sk) not in (None, sk)
            if diff or hit != cid or other:
                out["changed_items"].append({"id": hit, "changed": diff, "seen_as": cid,
                                             "secondary_key_differs": other})
        elif kind == "historical":
            out["historical"].append({"id": hit, "seen_as": cid, "candidate": c})
        elif kind == "pending":
            lead = next(l for l in st["pending_leads"] if I.lead_id(l) == hit)
            if (sk is not None and lead.get(I.sk) is None) or (hit != cid):
                out["enrich"].append({"id": hit, "candidate": c})
    w["seen_ids"], w["seen_sk"] = sorted(seen_ids), sorted(seen_sk, key=str)
    return classes, out


# ---------------------------------------------------------------- apply

def find_lead(I, st, lid):
    for n, l in enumerate(st["pending_leads"]):
        if I.lead_id(l) == lid:
            return n, l
    raise Fail(2, f"no pending lead {lid}")


def apply_change(pr, st, w, ch, run_date, plan, repair):
    I, P, op = pr.I, pr.P, ch.get("op")
    if repair and op not in REPAIR_OPS:
        raise Fail(2, f"{op} is not a repair operation")
    if not repair and op in REPAIR_OPS - {"lead.resolve"}:
        raise Fail(2, f"{op} is only allowed with --repair")
    log = {"op": op, "id": ch.get("id"), "reason": ch.get("reason")}
    if op == "lead.add":
        meth, per = ch["method"], ch["period"]
        if per not in plan["methods"].get(meth, {}).get("periods", []):
            raise Fail(2, f"lead period {per} is not a planned period of {meth}")
        lid = ch.get("id") or I.derive(ch["name"])
        sk = ch.get(I.sk)
        idx = I.index(st)
        for kind in ("item", "historical", "rejected", "pending"):
            if Ident.match(idx, kind, lid, sk):
                raise Fail(2, f"lead {lid} already exists as {kind}")
        lead = {"id": lid, "name": ch["name"], "first_seen": run_date, "category": ch["category"],
                "method": meth, "period": per}
        if I.sk:
            lead[I.sk] = sk
        lead.update({k: v for k, v in ch.get("extra", {}).items() if k not in lead})
        st["pending_leads"].append(lead)
        log["id"] = lid
    elif op == "lead.enrich":
        _, lead = find_lead(I, st, ch["id"])
        lead.setdefault("id", ch["id"])
        for k, v in ch["set"].items():
            if k not in (I.sk, "name"):
                raise Fail(2, "lead.enrich may set only the secondary key and name")
            lead[k] = v
    elif op in ("lead.accept", "lead.reject", "lead.fail"):
        n, lead = find_lead(I, st, ch["id"])
        if ch["id"] in w["attempted"]:
            raise Fail(2, f"lead {ch['id']} was already attempted in this run")
        w["attempted"].append(ch["id"])
        w["counters"]["verify"] += 1
        if op == "lead.fail":
            log["temporary"] = True
        else:
            st["pending_leads"].pop(n)
            if op == "lead.accept":
                item = dict(ch["item"])
                if item.get("relevance") not in P["item_relevance"]:
                    raise Fail(2, "accepted items need an allowed relevance; reject low relevance")
                item.update({"first_seen": lead["first_seen"], "last_seen": run_date, "last_verified": run_date,
                             "status": "active", "report": RUN_REPORT})
                if I.sk and item.get(I.sk) is None:
                    item[I.sk] = lead.get(I.sk)
                st["items"][ch["id"]] = item
                log["discovery_period"] = lead["period"]
            else:
                if ch.get("relevance") not in P.get("reject_relevance", []):
                    raise Fail(2, "rejection needs an allowed rejection relevance")
                if not ch.get("reason"):
                    raise Fail(2, "rejection needs a reason")
                if P.get("rejected_ids"):
                    st.setdefault("rejected_ids", {})[ch["id"]] = ch.get(I.sk, lead.get(I.sk)) if I.sk else None
        log["discovery_period"] = lead["period"]
    elif op in ("lead.resolve", "lead.drop"):
        if not ch.get("reason"):
            raise Fail(2, f"{op} needs a reason")
        n, _ = find_lead(I, st, ch["id"])
        if op == "lead.resolve":
            m = ch["matched"]
            if m not in st["items"] and m not in st["historical_ids"] and m not in st.get("rejected_ids", {}):
                raise Fail(2, f"matched entry {m} does not exist")
            log["matched"] = m
        st["pending_leads"].pop(n)
    elif op == "screen.drop":
        if not ch.get("reason"):
            raise Fail(2, "screen.drop needs a reason")
        log["id"] = ch.get("id") or I.derive(ch["name"])
    elif op in ("item.observe", "item.verify", "item.rename", "item.deactivate", "item.add_alias"):
        item = st["items"].get(ch["id"])
        if item is None:
            raise Fail(2, f"no active item {ch['id']}")
        if op == "item.observe":
            item["last_seen"] = run_date
        elif op == "item.verify":
            if ch["id"] in w["reverified"]:
                raise Fail(2, "item already re-verified in this run")
            w["reverified"].append(ch["id"])
            w["counters"]["reverify"] += 1
            item.update(ch.get("set", {}))
            if "fingerprint" in ch:
                item["fingerprint"] = ch["fingerprint"]
            item["last_verified"] = item["last_seen"] = run_date
            if ch.get("material"):
                item["report"] = RUN_REPORT
            log.update(material=bool(ch.get("material")), changes=ch.get("changes"))
        elif op in ("item.rename", "item.add_alias"):
            old = item["name"] if op == "item.rename" else ch["alias"]
            if old not in item.setdefault("aliases", []):
                item["aliases"].append(old)
            if op == "item.rename":
                item["name"] = ch["new_name"]
                item["report"] = RUN_REPORT
        else:
            entry = {"inactive_since": run_date, "fingerprint": ch.get("fingerprint", item["fingerprint"]),
                     "report": RUN_REPORT}
            entry.update({k: item[k] for k in P.get("historical_keep", []) if k in item})
            st["historical_ids"][ch["id"]] = entry
            del st["items"][ch["id"]]
    elif op == "item.reactivate":
        if ch["id"] not in st["historical_ids"]:
            raise Fail(2, f"no historical entry {ch['id']}")
        old = st["historical_ids"].pop(ch["id"])
        item = dict(ch["item"])
        item.update({"first_seen": item.get("first_seen", old.get("inactive_since")), "last_seen": run_date,
                     "last_verified": run_date, "status": "active", "report": RUN_REPORT})
        st["items"][ch["id"]] = item
    elif op == "source.set_coverage":
        st["sources"][ch["method"]]["covered_through"] = ch["covered_through"]
        log["id"] = ch["method"]
    elif op == "baseline.set_window":
        st["baseline"]["window"] = {"from": ch["from"], "to": ch["to"]}
    else:
        raise Fail(2, f"unknown operation {op}")
    if repair and not ch.get("reason"):
        raise Fail(2, "repair operations need a reason")
    return log


def cmd_apply(pr, a):
    changes = read_json(a.file)
    if a.repair:
        if pr.has_stage():
            raise Fail(3, "a run is in progress; repairs apply to published state only")
        if git(pr.root, "status", "--porcelain", "--", "state.json"):
            raise Fail(3, "state.json has uncommitted changes")
        base, raw = pr.load_state()
        st, w = copy.deepcopy(base), {"attempted": [], "reverified": [], "counters": {}}
        logs = [apply_change(pr, st, w, ch, None, {"methods": {}}, True) for ch in changes]
        removed = [l["id"] for l in logs if l["op"] == "lead.resolve"]
        E, W = validate(st, pr.P, pr.root, base, {"repair": True, "removed_leads": removed})
        if E:
            raise Fail(2, "repair rejected", errors=E)
        atomic_write(pr.state_path, dump_state(st, detect_format(raw)))
        return {"applied": logs, "warnings": W}
    m = pr.require_stage()
    w = pr.work()
    st = copy.deepcopy(w["state"])
    trial = copy.deepcopy(w)
    logs = [apply_change(pr, st, trial, ch, m["run_date"], m["plan"], False) for ch in changes]
    removed = [l["id"] for l in w["log"] + logs if l["op"] in ("lead.accept", "lead.reject", "lead.resolve", "lead.drop")]
    ctx = {"run_date": m["run_date"], "lcd": m["lcd"], "budgets": m["budgets"],
           "counters": trial["counters"], "removed_leads": removed}
    E, W = validate(st, pr.P, pr.root, w["base"], ctx)
    if E:
        raise Fail(2, "batch rejected; nothing was applied", errors=E)
    trial["state"], trial["log"] = st, w["log"] + logs
    pr.save(work=trial)
    return {"applied": len(logs), "results": [l for l in logs if l["op"] in ("lead.accept", "lead.reject", "lead.add")],
            "counters": trial["counters"], "warnings": W}


# ---------------------------------------------------------------- queue / show

def sort_key(order, I):
    def key(l):
        parts = []
        for f in order:
            v = l.get("name", "").lower() if f == "name_ci" else l.get(f)
            parts.append((v is None, v if v is not None else 0))
        return parts + [(False, I.lead_id(l))]
    return key


def cmd_queue(pr, a):
    m = pr.require_stage()
    w = pr.work()
    st, I, q = w["state"], pr.I, pr.P["queue"]
    left = m["budgets"]["verify"] - w["counters"]["verify"]
    n = max(0, min(a.n, left))
    pool = [l for l in st["pending_leads"] if I.lead_id(l) not in w["attempted"]]
    rq = q.get("reserve")
    r = min(n, math.ceil(rq["fraction"] * n)) if rq and rq.get("round") == "up" else (min(n, int(rq["fraction"] * n)) if rq else 0)
    reserve = sorted(pool, key=sort_key(rq["order"], I))[:r] if rq else []
    taken = {I.lead_id(l) for l in reserve}
    rest = [l for l in sorted(pool, key=sort_key(q["order"], I)) if I.lead_id(l) not in taken][:n - r]
    interval = dt.timedelta(days=m["reverify_interval_days"])
    rd = D(m["run_date"])
    due = sorted(((v["last_verified"], k) for k, v in st["items"].items()
                  if D(v["last_verified"]) + interval <= rd and k not in w["reverified"]))
    rleft = m["budgets"]["reverify"] - w["counters"]["reverify"]
    return {"reserve": reserve, "normal": rest, "verify_remaining": left,
            "reverify": [{"id": k, **compact(st["items"][k])} for _, k in due[:max(0, rleft)]],
            "reverify_due_total": len(due)}


def compact(item):
    return {k: v for k, v in item.items() if k not in ("report",)}


def cmd_show(pr, a):
    st = pr.work()["state"] if pr.has_stage() else pr.load_state()[0]
    out = {}
    for i in a.id:
        if i in st["items"]:
            out[i] = {"kind": "item", **st["items"][i]}
        elif i in st["historical_ids"]:
            out[i] = {"kind": "historical", **st["historical_ids"][i]}
        elif i in st.get("rejected_ids", {}):
            out[i] = {"kind": "rejected", pr.I.sk: st["rejected_ids"][i]}
        else:
            lead = next((l for l in st["pending_leads"] if pr.I.lead_id(l) == i), None)
            out[i] = {"kind": "pending", **lead} if lead else {"kind": "unknown"}
    return out


# ---------------------------------------------------------------- coverage, summary, finish

def coverage(m, w):
    """Advance coverage only over contiguous fully checked periods; derive run status."""
    plan, st = m["plan"], copy.deepcopy(w["state"])
    total = done_n = 0
    result = {}
    for meth, pm in plan["methods"].items():
        src = st["sources"].setdefault(meth, {"from": pm["from"], "covered_through": None, "last_status": None})
        ops = [o for o in w["ops"] if o["method"] == meth]
        covered, first_open, worked, any_done = src.get("covered_through"), None, bool(ops), False
        for per in pm["periods"]:
            complete = [o["op"] for o in ops if o["period"] == per and o["status"] in ("complete", "reused")]
            total += len(pm["operations"])
            done_n += len(set(complete))
            any_done = any_done or bool(complete)
            if first_open is None and set(pm["operations"]) <= set(complete):
                covered = per.split("..")[1]
            elif first_open is None:
                first_open = (per, sorted(set(complete)))
        src["covered_through"] = covered
        if first_open and first_open[1]:
            src["checkpoint"] = {"period": first_open[0], "config": pm["config"], "done": first_open[1],
                                 "report": RUN_REPORT}
        elif not first_open or (src.get("checkpoint") or {}).get("period") != first_open[0]:
            src.pop("checkpoint", None)
        if worked:
            src["last_status"] = "complete" if not first_open else ("partial" if any_done else "failed")
        result[meth] = {"before": pm["covered_through"], "after": covered, "periods": pm["periods"],
                        "status": src["last_status"] if worked else "not worked"}
    bl = st["baseline"]
    if bl["status"] != "complete":
        bl["window"] = plan["window"]
        enabled = [st["sources"][x] for x in plan["methods"]]
        bl["status"] = "complete" if all(s["covered_through"] and D(s["covered_through"]) >= D(bl["window"]["to"])
                                         for s in enabled) else "in_progress"
    status = "complete" if done_n == total else ("partial" if done_n else "failed")
    return st, result, status


def acted_ids(w):
    return sorted({l["id"] for l in w["log"] if l["op"] != "item.observe" and l.get("id")})


def cmd_summary(pr, a):
    m = pr.require_stage()
    w = pr.work()
    st, cov, status = coverage(m, w)
    by = {}
    for l in w["log"]:
        by.setdefault(l["op"], []).append(l)
    leads = st["pending_leads"]
    added = [l for l in leads if l["first_seen"] == m["run_date"]]
    failed = by.get("lead.fail", [])
    backlog = {}
    for l in leads:
        backlog.setdefault(l.get("category"), {}).setdefault(l["first_seen"], 0)
        backlog[l.get("category")][l["first_seen"]] += 1
    md_cov = ["| Method | Before | After | Periods | Status |", "|---|---|---|---|---|"]
    md_cov += [f"| {k} | {v['before']} | {v['after']} | {', '.join(v['periods']) or 'none'} | {v['status']} |"
               for k, v in cov.items()]
    md_cov += ["", "| Method | Period | Operation | Status | Detail |", "|---|---|---|---|---|"]
    for o in w["ops"]:
        detail = o.get("evidence") or "; ".join(o.get("reasons", [])) or \
            ", ".join(f"{k}={o[k]}" for k in ("total_count", "items_read", "requests") if k in o)
        md_cov.append(f"| {o['method']} | {o['period']} | `{o['op']}` | {o['status']} | {detail} |")
    md_leads = [f"Pending leads: {len(w['base']['pending_leads'])} before → {len(leads)} after. "
                f"All pending leads remain in `state.json`.", "",
                f"Added this run ({len(added)}): " + (", ".join(f"`{pr.I.lead_id(l)}` (cat. {l.get('category')})" for l in added) or "None"), "",
                f"Temporary failures this run ({len(failed)}): " + ("; ".join(f"`{l['id']}` — {l.get('reason')}" for l in failed) or "None"), "",
                "| Category | First seen | Leads |", "|---|---|---|"]
    md_leads += [f"| {c} | {fs} | {n} |" for c in sorted(backlog, key=lambda x: (x is None, x))
                 for fs, n in sorted(backlog[c].items())]
    md_changes = [f"- `{k}`: {len(v)}" for k, v in sorted(by.items())]
    return {"derived_status": status, "type": m["plan"]["type"], "counters": w["counters"], "budgets": m["budgets"],
            "coverage": cov, "acted_ids": acted_ids(w),
            "markdown": {"coverage": "\n".join(md_cov), "unverified_leads": "\n".join(md_leads),
                         "state_changes": "\n".join(md_changes) or "None"}}


def cmd_finish(pr, a):
    if not pr.has_stage():
        raise Fail(3, "no run in progress")
    m = pr.manifest()
    if m["phase"] == "published":
        raise Fail(3, "already published; commit the files", files=sorted(m["targets"]))
    w = pr.work()
    if m["phase"] == "staged":
        new_st, cov, derived = coverage(m, w)
        if a.status == "failed":
            if not a.fatal and derived != "failed":
                raise Fail(2, f"operation outcomes give status {derived}; use --fatal with a reason for a fatal error")
            new_st = copy.deepcopy(w["base"])
        elif a.status != derived:
            raise Fail(2, f"requested status {a.status} does not match the operation outcomes ({derived})")
        target, n = os.path.join("reports", "daily", f"{m['run_date']}.md"), 2
        while os.path.exists(pr.p(target)):
            target, n = os.path.join("reports", "daily", f"{m['run_date']}-{n}.md"), n + 1
        with open(a.report, encoding="utf-8") as f:
            report = f.read()
        problems = []
        if m["run_date"] not in report:
            problems.append("report does not state the execution date")
        if not re.search(r"Status:\W*" + a.status, report):
            problems.append(f"report does not state Status: {a.status}")
        if a.fatal and a.fatal not in report:
            problems.append("report does not state the fatal error reason")
        if m.get("publication_mode") == "manual-supervised" and "pending maintainer push" not in report.lower():
            problems.append("manual-supervised run: report must state that publication is pending maintainer push")
        if a.status != "failed":
            low = report.lower()
            problems += [f"report does not list {i}" for i in acted_ids(w) if i.lower() not in low]
        if problems:
            raise Fail(2, "report rejected", problems=problems)
        if not OPS_RE.search(report):
            ops = [{k: o[k] for k in ("method", "period", "op", "status", "evidence") if k in o} for o in w["ops"]]
            report = report.rstrip("\n") + "\n\n<!-- urf-ops\n" + json.dumps({"ops": ops}) + "\n-->\n"
        rel = target.replace(os.sep, "/")
        new_st["last_run"] = {"date": m["run_date"], "type": m["plan"]["type"], "status": a.status, "report": rel}
        ctx = {"run_date": m["run_date"], "lcd": m["lcd"], "budgets": m["budgets"], "counters": w["counters"],
               "removed_leads": [l["id"] for l in w["log"] if l["op"] in ("lead.accept", "lead.reject", "lead.resolve", "lead.drop")]}
        if a.status == "failed":
            ctx["removed_leads"] = []
        E, _ = validate(new_st, pr.P, pr.root, w["base"], ctx)
        if E:
            raise Fail(2, "final state rejected; nothing was published", errors=E)
        new_st = json.loads(json.dumps(new_st).replace(json.dumps(RUN_REPORT), json.dumps(rel)))
        state_text = dump_state(new_st, m["format"])
        w["publish"] = {"report": report, "state": state_text}
        m.update(phase="publishing", status=a.status, targets={
            rel: sha(report.encode("utf-8")), "state.json": sha(state_text.encode("utf-8"))})
        pr.save(work=w)
        pr.save(manifest=m)
    rel = next(t for t in m["targets"] if t != "state.json")
    atomic_write(pr.p(rel), w["publish"]["report"])
    atomic_write(pr.state_path, w["publish"]["state"])
    m["phase"] = "published"
    pr.save(manifest=m)
    t = m["plan"]["type"]
    out = {"published": sorted(m["targets"]), "status": m["status"],
           "commit": f"git add state.json {rel} && git commit -m \"research: {m['run_date']} {t} {m['status']}\""}
    if m.get("publication_mode") == "manual-supervised":
        out["written_locally"] = out.pop("published")
        out["publication_mode"] = "manual-supervised"
        out["remote_publication"] = ("pending maintainer push: files are written locally; after the local commit "
                                     "the run is not remotely published until the maintainer pushes; send no email")
    return out


def cmd_validate(pr, a):
    if a.published or not pr.has_stage():
        st, _ = pr.load_state()
        E, W = validate(st, pr.P, pr.root)
    else:
        m, w = pr.manifest(), pr.work()
        E, W = validate(w["state"], pr.P, pr.root, w["base"], {"run_date": m["run_date"], "lcd": m["lcd"],
                        "budgets": m["budgets"], "counters": w["counters"],
                        "removed_leads": [l["id"] for l in w["log"]]})
    if E:
        raise Fail(2, "validation failed", errors=E, warnings=W)
    return {"valid": True, "warnings": W}


# ---------------------------------------------------------------- CLI

def main(argv=None):
    ap = argparse.ArgumentParser(prog="urf.py")
    ap.add_argument("--root", default=".")
    ap.add_argument("--profile")
    sp = ap.add_subparsers(dest="cmd", required=True)
    b = sp.add_parser("begin")
    b.add_argument("--now", required=True)
    b.add_argument("--config", required=True)
    for name in ("record", "apply"):
        p = sp.add_parser(name)
        p.add_argument("--file", required=True)
        if name == "apply":
            p.add_argument("--repair", action="store_true")
    sp.add_parser("queue").add_argument("--n", type=int, required=True)
    sp.add_parser("show").add_argument("--id", action="append", required=True)
    sp.add_parser("summary")
    f = sp.add_parser("finish")
    f.add_argument("--status", choices=["complete", "partial", "failed"], required=True)
    f.add_argument("--report", required=True)
    f.add_argument("--fatal")
    sp.add_parser("validate").add_argument("--published", action="store_true")
    sp.add_parser("discard")
    a = ap.parse_args(argv)
    try:
        pr = Project(os.path.abspath(a.root), a.profile)
        res = globals()["cmd_" + a.cmd](pr, a)
        print(json.dumps(res, indent=1, ensure_ascii=False, default=str))
        return 0
    except Fail as e:
        print(json.dumps({"error": e.message, **e.extra}, indent=1, ensure_ascii=False, default=str))
        return e.code
    except (KeyError, TypeError, ValueError) as e:
        print(json.dumps({"error": f"invalid input: {type(e).__name__}: {e}"}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
