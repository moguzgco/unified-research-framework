"""Regression tests for tools/urf.py. Synthetic data only.

Run from the repository root: python3 -m unittest discover -s tools/tests
"""
import contextlib
import copy
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import urf  # noqa: E402

PROFILE = os.path.join(HERE, "fixtures", "repo-scout-profile.json")
NEW, EST, LISTS, WEB = "github.com/search-new", "github.com/search-established", "github.com/lists", "web-search"
Q1, Q2 = "topic:a", "topic:b"


def base_state():
    return {"schema_version": 1,
            "last_run": {"date": None, "type": None, "status": None, "report": None},
            "baseline": {"status": "not_started", "window": {"from": None, "to": None}},
            "sources": {}, "items": {}, "historical_ids": {}, "pending_leads": []}


def item(name, rid, **kw):
    v = {"name": name, "repo_id": rid, "created": "2026-01-01T00:00:00Z", "license": "MIT",
         "latest_release": "v1.0.0", "relevance": "medium", "category": 1, "first_seen": "2026-09-01",
         "last_seen": "2026-09-01", "last_verified": "2026-09-01", "status": "active",
         "fingerprint": {"latest_release": "v1.0.0", "latest_tag": "v1.0.0", "archived": False,
                         "license": "MIT", "name": name, "default_branch": "main"},
         "report": "reports/daily/2026-09-01.md"}
    v.update(kw)
    return v


def lead(name, rid, cat=1, first="2026-09-01", method=NEW, per="2026-08-01..2026-08-31", with_id=True):
    l = {"name": name, "repo_id": rid, "first_seen": first, "category": cat, "method": method, "period": per}
    if with_id:
        l["id"] = "github.com/" + name.lower()
    return l


def cfg(methods=None, budgets=None, **kw):
    c = {"contract": "continuous", "push_available": True, "baseline_window_days": 60,
         "budgets": budgets or {"search": 20, "verify": 60, "reverify": 10},
         "methods": methods or {NEW: {"config": "depth=30 forks=exclude", "operations": [Q1, Q2]},
                                EST: {"config": "depth=30 forks=exclude stars=500", "operations": [Q1, Q2]}}}
    c.update(kw)
    return c


def op(method, per, q, status="complete", cands=(), **kw):
    r = {"method": method, "period": per, "op": q, "status": status, "requests": 1, "incomplete_results": False,
         "fields_complete": True, "pages_read": 1, "pages_required": 1, "total_count": len(cands),
         "items_read": len(cands), "depth": 30, "candidates": list(cands)}
    r.update(kw)
    return r


class Repo:
    """A throwaway project repository."""

    def __init__(self, state, reports=("2026-09-01",)):
        self.root = tempfile.mkdtemp(prefix="urf-test-")
        os.makedirs(os.path.join(self.root, "framework"))
        os.makedirs(os.path.join(self.root, "reports", "daily"))
        shutil.copy(PROFILE, os.path.join(self.root, "framework", "state-profile.json"))
        self.write("PROJECT.md", "# Test\n")
        self.write(".gitignore", ".urf/\n")
        for r in reports:
            self.write(f"reports/daily/{r}.md", f"# report {r}\n")
        self.write("state.json", json.dumps(state, indent=2) + "\n")
        self.git("init", "-q")
        self.commit("init")

    def write(self, rel, text):
        p = os.path.join(self.root, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as f:
            f.write(text)

    def jfile(self, name, obj):
        p = os.path.join(self.root, ".urf-in-" + name + ".json")
        with open(p, "w") as f:
            json.dump(obj, f)
        return p

    def git(self, *a):
        subprocess.run(["git", "-C", self.root, "-c", "user.name=t", "-c", "user.email=t@t", *a],
                       check=True, capture_output=True)

    def commit(self, msg):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", msg, "--allow-empty")

    def run(self, *argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = urf.main(["--root", self.root, *argv])
        return code, json.loads(buf.getvalue())

    def ok(self, *argv):
        code, out = self.run(*argv)
        assert code == 0, out
        return out

    def state(self):
        with open(os.path.join(self.root, "state.json")) as f:
            return json.load(f)

    def raw_state(self):
        with open(os.path.join(self.root, "state.json")) as f:
            return f.read()

    def begin(self, now="2026-10-10T10:00:00Z", c=None):
        return self.ok("begin", "--now", now, "--config", self.jfile("cfg", c or cfg()))

    def record(self, rec):
        return self.ok("record", "--file", self.jfile("op", rec))

    def apply(self, changes, *extra):
        return self.run("apply", "--file", self.jfile("ch", changes), *extra)

    def report(self, text):
        p = os.path.join(self.root, ".urf-in-report.md")
        with open(p, "w") as f:
            f.write(text)
        return p

    def finish(self, status, text, *extra):
        return self.run("finish", "--status", status, "--report", self.report(text), *extra)

    def cleanup(self):
        shutil.rmtree(self.root, ignore_errors=True)


def incremental_state(**extra):
    st = base_state()
    st["baseline"] = {"status": "complete", "window": {"from": "2026-08-01", "to": "2026-09-29"}}
    st["sources"] = {NEW: {"from": "2026-08-01", "covered_through": "2026-10-08", "last_status": "complete"},
                     EST: {"from": "2026-08-01", "covered_through": "2026-10-08", "last_status": "complete"}}
    st["rejected_ids"] = {}
    st.update(extra)
    return st


PER = "2026-10-09..2026-10-09"


class Base(unittest.TestCase):
    def repo(self, state=None, **kw):
        r = Repo(state or incremental_state(), **kw)
        self.addCleanup(r.cleanup)
        return r

    def full_discovery(self, r, per=PER, cands=None):
        for m in (NEW, EST):
            for q in (Q1, Q2):
                r.record(op(m, per, q, cands=(cands or {}).get((m, q), [])))


# ------------------------------------------------------------------ coverage

class CoverageTests(Base):
    def test_utc_last_complete_day(self):
        r = self.repo()
        out = r.begin(now="2026-10-10T00:01:00Z")
        self.assertEqual(out["lcd"], "2026-10-09")
        self.assertEqual(out["plan"]["methods"][NEW]["periods"], [PER])
        r2 = self.repo()
        out = r2.begin(now="2026-10-09T23:59:00Z")
        self.assertEqual(out["plan"]["methods"][NEW]["periods"], [])  # nothing elapsed since 10-08

    def test_complete_advances_coverage(self):
        r = self.repo()
        r.begin()
        self.full_discovery(r)
        out = r.finish("complete", "Run 2026-10-10 Status: complete")
        st = r.state()
        self.assertEqual(st["sources"][NEW]["covered_through"], "2026-10-09")
        self.assertEqual(st["last_run"]["report"], "reports/daily/2026-10-10.md")
        self.assertIn("git commit", out[1]["commit"])

    def test_incomplete_op_partial_with_checkpoint(self):
        r = self.repo()
        r.begin()
        r.record(op(NEW, PER, Q1))
        r.record(op(NEW, PER, Q2, status="incomplete"))
        r.record(op(EST, PER, Q1))
        r.record(op(EST, PER, Q2))
        code, out = r.finish("complete", "2026-10-10 Status: complete")
        self.assertEqual(code, 2)
        r.ok("finish", "--status", "partial", "--report", r.report("2026-10-10 Status: partial"))
        st = r.state()
        self.assertEqual(st["sources"][NEW]["covered_through"], "2026-10-08")
        self.assertEqual(st["sources"][NEW]["checkpoint"]["done"], [Q1])
        self.assertEqual(st["sources"][NEW]["checkpoint"]["report"], "reports/daily/2026-10-10.md")
        self.assertEqual(st["sources"][NEW]["last_status"], "partial")
        self.assertEqual(st["sources"][EST]["covered_through"], "2026-10-09")

    def test_depth_limit_alone_is_not_completion(self):
        r = self.repo()
        r.begin()
        out = r.record(op(NEW, PER, Q1, total_count=500, items_read=30, pages_read=1, pages_required=1,
                          incomplete_results=True))
        self.assertEqual(out["status"], "incomplete")
        out = r.record(op(NEW, PER, Q2, total_count=500, items_read=25))
        self.assertEqual(out["status"], "incomplete")  # fewer than min(depth, total)

    def test_bounded_search_complete_and_relevance_independent(self):
        r = self.repo()
        r.begin()
        cands = [{"name": f"o/r{i}", "repo_id": 100 + i} for i in range(30)]
        out = r.record(op(NEW, PER, Q1, cands=cands, total_count=500, items_read=30))
        self.assertEqual(out["status"], "complete")
        drops = [{"op": "screen.drop", "name": c["name"], "reason": "out of scope"} for c in cands]
        self.assertEqual(r.apply(drops)[0], 0)  # every candidate dropped: coverage still counts
        r.record(op(NEW, PER, Q2))
        r.record(op(EST, PER, Q1))
        r.record(op(EST, PER, Q2))
        text = "2026-10-10 Status: complete " + " ".join("github.com/" + c["name"] for c in cands)
        r.ok("finish", "--status", "complete", "--report", r.report(text))
        self.assertEqual(r.state()["sources"][NEW]["covered_through"], "2026-10-09")

    def test_failed_run_publishes_only_last_run(self):
        st = incremental_state(pending_leads=[lead("a/x", 1)])
        r = self.repo(st)
        before = r.state()
        r.begin()
        r.record(op(NEW, PER, Q1))
        self.assertEqual(r.apply([{"op": "lead.reject", "id": "github.com/a/x", "relevance": "low", "reason": "r"}])[0], 0)
        code, _ = r.finish("failed", "2026-10-10 Status: failed")
        self.assertEqual(code, 2)  # partial outcomes need --fatal to be called failed
        r.ok("finish", "--status", "failed", "--fatal", "tool crash", "--report",
             r.report("2026-10-10 Status: failed. tool crash"))
        after = r.state()
        self.assertEqual(after["last_run"]["status"], "failed")
        after["last_run"] = before["last_run"]
        self.assertEqual(after, before)
        r.commit("failed run")
        out = r.begin(now="2026-10-11T08:00:00Z")
        self.assertTrue(any("preserved" in w for w in out["warnings"]))
        self.assertTrue(os.path.isdir(os.path.join(r.root, ".urf", "preserved")))

    def test_baseline_months_window_and_completion(self):
        r = self.repo(dict(base_state(), rejected_ids={}))
        out = r.begin(now="2026-10-10T09:00:00Z")
        pm = out["plan"]["methods"]
        self.assertEqual(out["plan"]["window"], {"from": "2026-08-10", "to": "2026-10-09"})
        self.assertEqual(pm[NEW]["periods"], ["2026-08-10..2026-08-31", "2026-09-01..2026-09-30",
                                              "2026-10-01..2026-10-09"])
        self.assertEqual(pm[EST]["periods"], ["2026-08-10..2026-10-09"])
        for per in pm[NEW]["periods"][:2]:
            r.record(op(NEW, per, Q1))
            r.record(op(NEW, per, Q2))
        for q in (Q1, Q2):
            r.record(op(EST, "2026-08-10..2026-10-09", q))
        r.ok("finish", "--status", "partial", "--report", r.report("2026-10-10 Status: partial"))
        st = r.state()
        self.assertEqual(st["baseline"]["status"], "in_progress")
        self.assertEqual(st["sources"][NEW]["covered_through"], "2026-09-30")
        self.assertNotIn("checkpoint", st["sources"][NEW])

    def test_recency_method(self):
        st = incremental_state()
        st["sources"][WEB] = {"from": "2026-08-01", "covered_through": "2026-10-08", "last_status": "complete"}
        r = self.repo(st)
        c = cfg()
        c["methods"][WEB] = {"config": "depth=10", "operations": ["web q"]}
        out = r.begin(c=c)
        self.assertEqual(out["plan"]["methods"][WEB]["periods"], ["2026-10-10..2026-10-10"])
        self.full_discovery(r)
        r.record({"method": WEB, "period": "2026-10-10..2026-10-10", "op": "web q", "status": "complete",
                  "requests": 1, "depth": 10, "results_available": 10, "results_screened": 10})
        r.ok("finish", "--status", "complete", "--report", r.report("2026-10-10 Status: complete"))
        self.assertEqual(r.state()["sources"][WEB]["covered_through"], "2026-10-10")

    def test_recency_baseline_completes_on_first_pass(self):
        r = self.repo(dict(base_state(), rejected_ids={}))
        c = cfg(methods={WEB: {"config": "depth=10", "operations": ["q"]}})
        r.begin(c=c)
        r.record({"method": WEB, "period": "2026-10-10..2026-10-10", "op": "q", "status": "complete",
                  "requests": 1, "depth": 10, "results_available": 3, "results_screened": 3})
        r.ok("finish", "--status", "complete", "--report", r.report("2026-10-10 Status: complete"))
        self.assertEqual(r.state()["baseline"]["status"], "complete")

    def test_source_baseline_anchor(self):
        st = incremental_state()
        r = self.repo(st)
        c = cfg()
        c["methods"][LISTS] = {"config": "files=README.md", "operations": ["o/list"]}
        out = r.begin(c=c)
        self.assertEqual(out["plan"]["methods"][LISTS]["from"], "2026-08-10")  # lcd 10-09 minus 60 days
        self.assertEqual(out["plan"]["methods"][LISTS]["periods"], ["2026-08-10..2026-10-09"])

    def test_search_budget_warning_and_enforcement(self):
        r = self.repo()
        out = r.begin(c=cfg(budgets={"search": 3, "verify": 5, "reverify": 1}))
        self.assertTrue(any("below one pass" in w for w in out["warnings"]))
        for q in (Q1, Q2):
            r.record(op(NEW, PER, q))
        r.record(op(EST, PER, Q1))
        code, out = r.run("record", "--file", r.jfile("op", op(EST, PER, Q2)))
        self.assertEqual(code, 2)


# ------------------------------------------------------------------ checkpoints

class CheckpointTests(Base):
    def cp_state(self, report="reports/daily/2026-10-09.md", per="2026-10-09..2026-10-09", config="depth=30 forks=exclude"):
        st = incremental_state()
        st["sources"][NEW]["checkpoint"] = {"period": per, "config": config, "done": [Q1, "removed q"], "report": report}
        return st

    def test_reuse_with_ops_block_and_removed_query(self):
        rep = "<!-- urf-ops\n" + json.dumps({"ops": [{"method": NEW, "period": PER, "op": Q1, "status": "complete"}]}) + "\n-->\n"
        r = self.repo(self.cp_state(), reports=("2026-09-01",))
        r.write("reports/daily/2026-10-09.md", "x\n" + rep)
        r.commit("cp")
        out = r.begin()
        reusable = out["plan"]["methods"][NEW]["reusable"]
        self.assertEqual(reusable, [{"op": Q1, "evidence": "reports/daily/2026-10-09.md", "needs_confirmation": False}])
        r.record({"method": NEW, "period": PER, "op": Q1, "reuse": True})
        r.record(op(NEW, PER, Q2))
        r.record(op(EST, PER, Q1))
        r.record(op(EST, PER, Q2))
        r.ok("finish", "--status", "complete", "--report", r.report("2026-10-10 Status: complete"))
        src = r.state()["sources"][NEW]
        self.assertEqual(src["covered_through"], "2026-10-09")
        self.assertNotIn("checkpoint", src)

    def test_legacy_report_needs_confirmation(self):
        r = self.repo(self.cp_state())
        r.write("reports/daily/2026-10-09.md", "legacy report\n")
        r.commit("cp")
        out = r.begin()
        self.assertTrue(out["plan"]["methods"][NEW]["reusable"][0]["needs_confirmation"])
        code, _ = r.run("record", "--file", r.jfile("op", {"method": NEW, "period": PER, "op": Q1, "reuse": True}))
        self.assertEqual(code, 2)
        r.record({"method": NEW, "period": PER, "op": Q1, "reuse": True, "confirmed": True})

    def test_invalidation(self):
        cases = {"period": self.cp_state(per="2026-10-01..2026-10-09"),
                 "config": self.cp_state(config="depth=20 forks=exclude"),
                 "report": self.cp_state(report="reports/daily/missing.md")}
        for name, st in cases.items():
            with self.subTest(name):
                if name == "report":
                    r = self.repo(st)  # a missing checkpoint report fails published validation
                    code, out = r.run("begin", "--now", "2026-10-10T10:00:00Z", "--config", r.jfile("cfg", cfg()))
                    self.assertEqual(code, 3)
                    continue
                r = self.repo(st)
                r.write("reports/daily/2026-10-09.md", "x\n")
                r.commit("cp")
                out = r.begin()
                self.assertEqual(out["plan"]["methods"][NEW]["reusable"], [])

    def test_incremental_checkpoint_dropped_when_period_moves(self):
        r = self.repo(self.cp_state(per="2026-10-08..2026-10-08"))
        r.write("reports/daily/2026-10-09.md", "x\n")
        r.commit("cp")
        r.begin()
        self.full_discovery(r)
        r.ok("finish", "--status", "complete", "--report", r.report("2026-10-10 Status: complete"))
        self.assertNotIn("checkpoint", r.state()["sources"][NEW])


# ------------------------------------------------------------------ leads, items, identity

class LifecycleTests(Base):
    def test_classification_and_lead_add(self):
        st = incremental_state(items={"github.com/a/item": item("a/item", 1)},
                               pending_leads=[lead("a/lead", None)], rejected_ids={"github.com/a/rej": 3})
        st["historical_ids"] = {"github.com/a/old": {"inactive_since": "2026-09-20", "fingerprint": {},
                                                    "report": "reports/daily/2026-09-01.md", "repo_id": 4,
                                                    "name": "a/old", "aliases": []}}
        r = self.repo(st)
        r.begin()
        cands = [{"name": "A/Item", "repo_id": 1, "archived": True}, {"name": "a/lead", "repo_id": 2},
                 {"name": "a/rej", "repo_id": 3}, {"name": "new/name", "repo_id": 4}, {"name": "b/new", "repo_id": 5},
                 {"name": "b/new", "repo_id": 5}]
        out = r.record(op(NEW, PER, Q1, cands=cands))
        self.assertEqual(out["classes"], {"new": 1, "item": 1, "historical": 1, "rejected": 1, "pending": 1, "dup_in_run": 1})
        self.assertEqual(out["changed_items"][0]["changed"], {"archived": [False, True]})
        self.assertEqual(out["historical"][0]["id"], "github.com/a/old")  # renamed repo recognised by repo_id
        self.assertEqual(out["enrich"][0]["id"], "github.com/a/lead")
        code, _ = r.apply([{"op": "lead.add", "name": "a/item", "repo_id": 9, "category": 1, "method": NEW, "period": PER}])
        self.assertEqual(code, 2)  # existing item ID
        code, _ = r.apply([{"op": "lead.add", "name": "x/y", "repo_id": 1, "category": 1, "method": NEW, "period": PER}])
        self.assertEqual(code, 2)  # existing secondary key
        code, _ = r.apply([{"op": "lead.add", "name": "x/y", "repo_id": 7, "category": 1, "method": NEW,
                            "period": "2026-01-01..2026-01-31"}])
        self.assertEqual(code, 2)  # period outside the run
        r.apply([{"op": "lead.enrich", "id": "github.com/a/lead", "set": {"repo_id": 2}},
                 {"op": "lead.add", "name": "b/new", "repo_id": 5, "category": 2, "method": NEW, "period": PER}])
        st = r.ok("show", "--id", "github.com/a/lead", "--id", "github.com/b/new")
        self.assertEqual(st["github.com/a/lead"]["repo_id"], 2)
        self.assertEqual(st["github.com/a/lead"]["first_seen"], "2026-09-01")
        self.assertEqual(st["github.com/b/new"]["first_seen"], "2026-10-10")

    def test_accept_reject_fail_and_batch_atomicity(self):
        leads = [lead("a/one", 1, first="2026-09-02"), lead("a/two", 2), lead("a/three", 3, with_id=False)]
        r = self.repo(incremental_state(pending_leads=leads))
        r.begin()
        good = {"op": "lead.accept", "id": "github.com/a/one",
                "item": {k: v for k, v in item("a/one", 1).items() if k not in ("first_seen", "last_seen", "last_verified", "status", "report")}}
        bad = {"op": "lead.reject", "id": "github.com/a/two", "relevance": "high", "reason": "x"}
        code, _ = r.apply([good, bad])
        self.assertEqual(code, 2)
        self.assertEqual(r.ok("show", "--id", "github.com/a/one")["github.com/a/one"]["kind"], "pending")
        out = r.apply([good, {"op": "lead.reject", "id": "github.com/a/two", "relevance": "low", "reason": "placeholder"},
                       {"op": "lead.fail", "id": "github.com/a/three", "reason": "timeout"}])[1]
        self.assertEqual(out["counters"]["verify"], 3)
        self.assertEqual(out["results"][0]["discovery_period"], "2026-08-01..2026-08-31")
        code, _ = r.apply([{"op": "lead.accept", "id": "github.com/a/three", "item": good["item"]}])
        self.assertEqual(code, 2)  # attempted already
        self.full_discovery(r)
        code, out = r.finish("complete", "2026-10-10 Status: complete github.com/a/one github.com/a/two")
        self.assertEqual(code, 2)  # a/three (attempted) not listed
        r.ok("finish", "--status", "complete", "--report",
             r.report("2026-10-10 Status: complete github.com/a/one github.com/a/two github.com/a/three"))
        st = r.state()
        self.assertEqual(st["items"]["github.com/a/one"]["first_seen"], "2026-09-02")
        self.assertEqual(st["items"]["github.com/a/one"]["report"], "reports/daily/2026-10-10.md")
        self.assertEqual(st["rejected_ids"], {"github.com/a/two": 2})
        self.assertEqual([l["name"] for l in st["pending_leads"]], ["a/three"])
        self.assertNotIn("id", st["pending_leads"][0])  # legacy lead shape preserved

    def test_verification_budget(self):
        r = self.repo(incremental_state(pending_leads=[lead("a/one", 1), lead("a/two", 2)]))
        r.begin(c=cfg(budgets={"search": 20, "verify": 1, "reverify": 1}))
        code, out = r.apply([{"op": "lead.fail", "id": "github.com/a/one", "reason": "t"},
                             {"op": "lead.fail", "id": "github.com/a/two", "reason": "t"}])
        self.assertEqual(code, 2)
        self.assertIn("verify budget exceeded", " ".join(out["errors"]))

    def test_lead_drop_needs_reason_and_no_silent_removal(self):
        r = self.repo(incremental_state(pending_leads=[lead("a/one", 1)]))
        r.begin()
        self.assertEqual(r.apply([{"op": "lead.drop", "id": "github.com/a/one"}])[0], 2)
        self.assertEqual(r.apply([{"op": "lead.drop", "id": "github.com/a/one", "reason": "duplicate of upstream"}])[0], 0)

    def test_deactivate_keeps_identity_and_reactivate(self):
        st = incremental_state(items={"github.com/a/one": item("a/one", 11, aliases=["old/one"])})
        r = self.repo(st)
        r.begin()
        r.apply([{"op": "item.deactivate", "id": "github.com/a/one", "reason": "archived"}])
        h = r.ok("show", "--id", "github.com/a/one")["github.com/a/one"]
        self.assertEqual((h["kind"], h["repo_id"], h["name"], h["aliases"]), ("historical", 11, "a/one", ["old/one"]))
        out = r.record(op(NEW, PER, Q1, cands=[{"name": "moved/one", "repo_id": 11}]))
        self.assertEqual(out["historical"][0]["id"], "github.com/a/one")
        code, _ = r.apply([{"op": "lead.add", "name": "moved/one", "repo_id": 11, "category": 1, "method": NEW, "period": PER}])
        self.assertEqual(code, 2)  # reappearance is not a new lead
        new_item = {k: v for k, v in item("moved/one", 11, aliases=["a/one"]).items() if k != "status"}
        r.apply([{"op": "item.reactivate", "id": "github.com/a/one", "item": new_item}])
        self.assertEqual(r.ok("show", "--id", "github.com/a/one")["github.com/a/one"]["kind"], "item")

    def test_reverification_order_and_budget(self):
        items = {f"github.com/a/i{n}": item(f"a/i{n}", n, last_verified=d)
                 for n, d in [(1, "2026-09-05"), (2, "2026-09-01"), (3, "2026-09-01"), (4, "2026-10-01")]}
        r = self.repo(incremental_state(items=items))
        r.begin(c=cfg(budgets={"search": 20, "verify": 5, "reverify": 2}))
        q = r.ok("queue", "--n", "5")
        self.assertEqual([x["id"] for x in q["reverify"]], ["github.com/a/i2", "github.com/a/i3"])
        self.assertEqual(q["reverify_due_total"], 3)
        r.apply([{"op": "item.verify", "id": "github.com/a/i2", "fingerprint": items["github.com/a/i2"]["fingerprint"]}])
        self.assertEqual([x["id"] for x in r.ok("queue", "--n", "5")["reverify"]], ["github.com/a/i3"])

    def test_disjoint_identity_invariant_on_published_state(self):
        st = incremental_state(items={"github.com/a/one": item("a/one", 1)}, pending_leads=[lead("a/one", None, with_id=False)])
        r = self.repo(st)
        code, out = r.run("validate", "--published")
        self.assertEqual(code, 2)
        self.assertIn("also a item entry", " ".join(out["errors"]))
        code, out = r.run("begin", "--now", "2026-10-10T10:00:00Z", "--config", r.jfile("cfg", cfg()))
        self.assertEqual(code, 3)

    def test_rename_alias_warning(self):
        st = incremental_state(items={"github.com/a/one": item("b/one", 1)})
        r = self.repo(st)
        self.assertTrue(r.ok("validate", "--published")["warnings"])

    def test_undeclared_top_level_and_status(self):
        for mutate in (lambda s: s.update(extra=1), lambda s: s["items"]["github.com/a/one"].update(status="inactive")):
            st = incremental_state(items={"github.com/a/one": item("a/one", 1)})
            mutate(st)
            r = self.repo(st)
            self.assertEqual(r.run("validate", "--published")[0], 2)


# ------------------------------------------------------------------ queue

class QueueTests(Base):
    def test_reserve_then_category_order(self):
        leads = [lead(f"c1/new{i}", 100 + i, cat=1, first="2026-10-08") for i in range(6)]
        leads += [lead(f"c2/old{i}", 200 + i, cat=2, first="2026-09-30") for i in range(3)]
        leads += [lead("c1/old", 300, cat=1, first="2026-09-30"), lead("C1/Alpha", 301, cat=1, first="2026-10-08")]
        r = self.repo(incremental_state(pending_leads=leads))
        r.begin()
        q = r.ok("queue", "--n", "8")
        self.assertEqual([l["name"] for l in q["reserve"]], ["c1/old", "c2/old0"])  # ceil(8 * 0.25) = 2
        self.assertEqual([l["name"] for l in q["normal"]],
                         ["C1/Alpha", "c1/new0", "c1/new1", "c1/new2", "c1/new3", "c1/new4"])
        self.assertEqual(q, r.ok("queue", "--n", "8"))  # deterministic

    def test_queue_respects_remaining_budget(self):
        r = self.repo(incremental_state(pending_leads=[lead(f"a/l{i}", i) for i in range(10)]))
        r.begin(c=cfg(budgets={"search": 20, "verify": 3, "reverify": 1}))
        q = r.ok("queue", "--n", "8")
        self.assertEqual(len(q["reserve"]) + len(q["normal"]), 3)


# ------------------------------------------------------------------ run lifecycle

class LifecycleRunTests(Base):
    def test_same_day_resume_and_stops(self):
        r = self.repo()
        r.begin()
        r.record(op(NEW, PER, Q1))
        out = r.begin()  # same day, same config: resume
        self.assertTrue(out["resumed"])
        code, out = r.run("begin", "--now", "2026-10-11T10:00:00Z", "--config", r.jfile("cfg", cfg()))
        self.assertEqual(code, 3)
        self.assertTrue(os.path.exists(os.path.join(r.root, ".urf", "run", "manifest.json")))
        code, out = r.run("begin", "--now", "2026-10-10T11:00:00Z", "--config",
                          r.jfile("cfg", cfg(budgets={"search": 5, "verify": 5, "reverify": 5})))
        self.assertEqual(code, 3)
        r.write("PROJECT.md", "# changed\n")
        code, out = r.run("begin", "--now", "2026-10-10T11:00:00Z", "--config", r.jfile("cfg", cfg()))
        self.assertEqual(code, 3)
        self.assertIn("configuration changed", " ".join(out["reasons"]))
        moved = r.ok("discard")["moved_to"]
        self.assertTrue(os.path.isdir(os.path.join(r.root, moved)))
        self.assertTrue(os.path.exists(os.path.join(r.root, moved, "work.json")))

    def test_unfinished_publication_and_cleanup(self):
        r = self.repo()
        r.begin()
        self.full_discovery(r)
        r.ok("finish", "--status", "complete", "--report", r.report("2026-10-10 Status: complete"))
        code, out = r.run("begin", "--now", "2026-10-10T12:00:00Z", "--config", r.jfile("cfg", cfg()))
        self.assertEqual(code, 3)
        self.assertEqual(sorted(out["files"]), ["reports/daily/2026-10-10.md", "state.json"])
        r.commit("research")
        out = r.begin(now="2026-10-10T12:00:00Z")
        self.assertIn("removed", " ".join(out["warnings"]))
        self.assertEqual(out["plan"]["methods"][NEW]["periods"], [])  # already covered through lcd

    def test_interrupted_publication_republishes(self):
        r = self.repo()
        r.begin()
        self.full_discovery(r)
        real = urf.atomic_write
        calls = []

        def crash(path, text):
            calls.append(path)
            if path.endswith("state.json"):
                raise OSError("simulated crash")
            real(path, text)
        urf.atomic_write = crash
        try:
            with self.assertRaises(OSError):  # the process dies between the two writes
                r.finish("complete", "2026-10-10 Status: complete")
        finally:
            urf.atomic_write = real
        code, out = r.run("begin", "--now", "2026-10-10T12:00:00Z", "--config", r.jfile("cfg", cfg()))
        self.assertEqual(code, 3)
        self.assertIn("finish", out["error"])
        r.ok("finish", "--status", "complete", "--report", r.report("ignored"))
        self.assertEqual(r.state()["sources"][NEW]["covered_through"], "2026-10-09")

    def test_dirty_tree_and_push_unavailable(self):
        r = self.repo()
        r.write("state.json", r.raw_state() + " ")
        code, out = r.run("begin", "--now", "2026-10-10T10:00:00Z", "--config", r.jfile("cfg", cfg()))
        self.assertEqual(code, 3)
        r2 = self.repo()
        code, out = r2.run("begin", "--now", "2026-10-10T10:00:00Z", "--config", r2.jfile("cfg", cfg(push_available=False)))
        self.assertEqual(code, 3)
        self.assertFalse(os.path.exists(os.path.join(r2.root, ".urf")))

    def test_unparsable_state_untouched(self):
        r = self.repo()
        r.write("state.json", "{broken")
        r.commit("broken")
        code, out = r.run("begin", "--now", "2026-10-10T10:00:00Z", "--config", r.jfile("cfg", cfg()))
        self.assertEqual(code, 3)
        self.assertEqual(r.raw_state(), "{broken")

    def test_deep_refused(self):
        r = self.repo()
        code, _ = r.run("begin", "--now", "2026-10-10T10:00:00Z", "--config", r.jfile("cfg", cfg(contract="deep")))
        self.assertEqual(code, 3)

    def test_report_suffix_and_format_preserved(self):
        st = incremental_state()
        r = self.repo(st, reports=("2026-09-01", "2026-10-10", "2026-10-10-2"))
        r.write("state.json", json.dumps(st, indent=1) + "\n")
        r.commit("indent 1")
        r.begin()
        self.full_discovery(r)
        out = r.ok("finish", "--status", "complete", "--report", r.report("2026-10-10 Status: complete"))
        self.assertIn("reports/daily/2026-10-10-3.md", out["published"])
        raw = r.raw_state()
        self.assertTrue(raw.startswith('{\n "schema_version"'))
        with open(os.path.join(r.root, "reports/daily/2026-10-10-3.md")) as f:
            self.assertIn("<!-- urf-ops", f.read())

    def test_one_line_lead_layout_preserved(self):
        st = incremental_state(pending_leads=[lead("a/one", 1), lead("a/two", 2)])
        r = self.repo(st)
        body = json.dumps({k: v for k, v in st.items() if k != "pending_leads"}, indent=1)[:-2]
        rows = ",\n".join("  " + json.dumps(l) for l in st["pending_leads"])
        r.write("state.json", body + ',\n "pending_leads": [\n' + rows + "\n ]\n}\n")
        r.commit("hybrid layout")
        r.begin()
        r.apply([{"op": "lead.add", "name": "b/new", "repo_id": 3, "category": 1, "method": NEW, "period": PER}])
        self.full_discovery(r)
        r.ok("finish", "--status", "complete", "--report", r.report("2026-10-10 Status: complete github.com/b/new"))
        lines = r.raw_state().splitlines()
        self.assertEqual(sum(1 for x in lines if x.startswith('  {"')), 3)

    def test_summary_compact_leads(self):
        leads = [lead(f"a/l{i}", i, first="2026-09-30") for i in range(50)]
        r = self.repo(incremental_state(pending_leads=leads))
        r.begin()
        r.apply([{"op": "lead.add", "name": "b/new", "repo_id": 999, "category": 2, "method": NEW, "period": PER}])
        s = r.ok("summary")
        md = s["markdown"]["unverified_leads"]
        self.assertIn("50 before → 51 after", md)
        self.assertIn("github.com/b/new", md)
        self.assertNotIn("a/l7", md)  # carried leads are counts, not rows
        self.assertEqual(s["derived_status"], "failed")  # nothing searched yet


# ------------------------------------------------------------------ publication mode

class PublicationModeTests(Base):
    AUTH = "Maintainer authorizes a supervised manual-push run on 2026-10-10."

    def manual(self, **kw):
        c = cfg(push_available=False, publication_mode="manual-supervised", maintainer_authorization=self.AUTH)
        c.update(kw)
        return c

    def begin_code(self, r, c):
        return r.run("begin", "--now", "2026-10-10T10:00:00Z", "--config", r.jfile("cfg", c))

    def test_automatic_unchanged(self):
        r = self.repo()
        self.assertEqual(self.begin_code(r, cfg(push_available=False))[0], 3)
        self.assertEqual(self.begin_code(r, cfg(publication_mode="automatic", push_available=False))[0], 3)
        r.begin()
        self.full_discovery(r)
        out = r.ok("finish", "--status", "complete", "--report", r.report("2026-10-10 Status: complete"))
        self.assertEqual(set(out), {"published", "status", "commit"})  # output unchanged

    def test_manual_supervised_accepted_and_recorded(self):
        r = self.repo()
        code, out = self.begin_code(r, self.manual())
        self.assertEqual(code, 0, out)
        with open(os.path.join(r.root, ".urf", "run", "manifest.json")) as f:
            self.assertEqual(json.load(f)["publication_mode"], "manual-supervised")

    def test_manual_supervised_needs_authorization_for_this_date(self):
        r = self.repo()
        for c in (self.manual(maintainer_authorization=None), self.manual(maintainer_authorization=""),
                  self.manual(maintainer_authorization="authorized for 2026-10-09")):
            code, out = self.begin_code(r, c)
            self.assertEqual(code, 3, out)
            self.assertIn("maintainer_authorization", out["error"])
        self.assertFalse(os.path.exists(os.path.join(r.root, ".urf")))

    def test_unsupported_mode_and_non_boolean_push(self):
        r = self.repo()
        for c in (cfg(publication_mode="manual"), cfg(publication_mode="unattended-manual"), cfg(push_available="yes")):
            self.assertEqual(self.begin_code(r, c)[0], 3)

    def test_manual_report_and_finish_output(self):
        r = self.repo()
        self.assertEqual(self.begin_code(r, self.manual())[0], 0)
        self.full_discovery(r)
        code, out = r.finish("complete", "2026-10-10 Status: complete")
        self.assertEqual(code, 2)
        self.assertIn("pending maintainer push", " ".join(out["problems"]))
        out = r.ok("finish", "--status", "complete", "--report",
                   r.report("2026-10-10 Status: complete. Publication: pending maintainer push."))
        self.assertNotIn("published", out)
        self.assertEqual(out["written_locally"], ["reports/daily/2026-10-10.md", "state.json"])
        self.assertIn("pending maintainer push", out["remote_publication"])
        self.assertEqual(r.state()["sources"][NEW]["covered_through"], "2026-10-09")  # coverage rules unchanged


# ------------------------------------------------------------------ repair and generic profile

class RepairTests(Base):
    def test_repair_ops(self):
        st = incremental_state(items={"github.com/a/one": item("b/one", 1)}, pending_leads=[lead("a/one", None, with_id=False)])
        r = self.repo(st)
        self.assertEqual(r.apply([{"op": "lead.add", "name": "x/y"}], "--repair")[0], 2)
        out = r.apply([{"op": "lead.resolve", "id": "github.com/a/one", "matched": "github.com/a/one", "reason": "already an item"},
                       {"op": "item.add_alias", "id": "github.com/a/one", "alias": "a/one", "reason": "renamed"},
                       {"op": "source.set_coverage", "method": NEW, "covered_through": "2026-10-01", "reason": "withdraw"}],
                      "--repair")
        self.assertEqual(out[0], 0, out)
        s = r.state()
        self.assertEqual(s["pending_leads"], [])
        self.assertEqual(s["sources"][NEW]["covered_through"], "2026-10-01")
        self.assertEqual(r.ok("validate", "--published")["warnings"], [])

    def test_research_run_cannot_repair(self):
        r = self.repo()
        r.begin()
        self.assertEqual(r.apply([{"op": "source.set_coverage", "method": NEW, "covered_through": "2026-10-09", "reason": "x"}])[0], 2)


class GenericProfileTests(unittest.TestCase):
    """A Job Scout-like profile: different IDs, no secondary key, no rejected_ids."""

    def test_toy_profile(self):
        prof = {"profile_version": 1, "id": {"prefix": "job:", "lowercase": False, "pattern": "^job:[A-Za-z0-9-]+$"},
                "secondary_key": None, "top_level": [], "rejected_ids": False, "item_required": ["name"],
                "item_relevance": ["fit"], "reject_relevance": ["no-fit"], "historical_keep": ["name"],
                "lead_required": ["name", "first_seen", "category", "method", "period"],
                "methods": {"board": {"baseline": "recency", "completion": [["listed", "==", "$read"]]}},
                "queue": {"order": ["first_seen", "name_ci"]}, "reverify_interval_days": 7}
        st = base_state()
        r = Repo(st)
        self.addCleanup(r.cleanup)
        with open(os.path.join(r.root, "framework", "state-profile.json"), "w") as f:
            json.dump(prof, f)
        r.commit("profile")
        c = {"contract": "continuous", "push_available": True, "baseline_window_days": 30,
             "budgets": {"search": 5, "verify": 5, "reverify": 5}, "methods": {"board": {"config": "", "operations": ["q"]}}}
        r.begin(c=c)
        out = r.record({"method": "board", "period": "2026-10-10..2026-10-10", "op": "q", "status": "complete",
                        "requests": 1, "listed": 2, "read": 2, "candidates": [{"name": "J-1"}, {"name": "J-2"}]})
        self.assertEqual(out["classes"]["new"], 2)
        r.apply([{"op": "lead.add", "name": "J-1", "category": 1, "method": "board", "period": "2026-10-10..2026-10-10"}])
        r.apply([{"op": "lead.accept", "id": "job:J-1", "item": {"name": "J-1", "relevance": "fit", "fingerprint": {}}}])
        r.ok("finish", "--status", "complete", "--report", r.report("2026-10-10 Status: complete job:J-1"))
        st = r.state()
        self.assertEqual(st["baseline"]["status"], "complete")
        self.assertIn("job:J-1", st["items"])


if __name__ == "__main__":
    unittest.main()
