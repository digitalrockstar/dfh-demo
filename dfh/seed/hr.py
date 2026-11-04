"""Module 9 seed: exits and notice periods, holidays, leave, rosters, attendance, onboarding tasks, job postings and applicants.
Own random stream (seed + 9), so no earlier module's numbers move. Attendance and rosters cover the 90 days before the demo date plus 14 days ahead.
Planted finding F9: the Hyderabad warehouse (see F1) lost 5 associates in 90 days, has about 11 percent absence and a thin hiring pipeline.
Also planted: three small stores where approving the pending leave on 3 Nov drops the store below two people on shift. Everything is synthetic."""
import json, random
from datetime import datetime, date, timedelta
from sqlalchemy import text, insert
from ..schema import metadata
from . import names as N

NOW = datetime(2026, 10, 31, 9, 0)
TODAY = NOW.date()
ATT_START = TODAY - timedelta(days=90)
ROSTER_END = TODAY + timedelta(days=14)
HOLIDAYS = [(date(2026, 1, 26), "Republic Day", None), (date(2026, 3, 21), "Eid al-Fitr (assumed date)", None), (date(2026, 5, 1), "May Day", None), (date(2026, 8, 15), "Independence Day", None),
            (date(2026, 9, 14), "Ganesh Chaturthi (assumed date)", "Maharashtra"), (date(2026, 10, 2), "Gandhi Jayanti", None), (date(2026, 10, 20), "Dussehra (assumed date)", None),
            (date(2026, 11, 1), "Karnataka Rajyotsava", "Karnataka"), (date(2026, 11, 8), "Diwali (assumed date)", None), (date(2026, 12, 25), "Christmas", None)]
HOL = {d: st for d, _, st in HOLIDAYS}
SHIFTS = {"MORNING": ("09:00", "17:00"), "EVENING": ("13:00", "21:30"), "GENERAL": ("09:30", "18:30")}
QUOTA = {"CL": 12, "SL": 8, "EL": 15, "WFH": 24}
REASONS = ["Better pay elsewhere", "Relocation", "Personal reasons", "Higher studies", "Performance", "Shift timings", "Moved to a competitor"]
TASKS = [("Offer letter signed", -3), ("ID and bank details submitted", -2), ("System login created", 0), ("Uniform and ID card issued", 1), ("Induction with manager", 3), ("Role training signed off", 10)]
SOURCES = ["Referral", "Naukri", "LinkedIn", "Walk-in", "Careers page"]
STAGES = ["Applied", "Screen", "Interview", "Offer", "Hired", "Rejected"]


def d_of(x): return x if isinstance(x, date) else date.fromisoformat(str(x)[:10])


def off_days(e): return {5, 6} if e["lt"] == "office" else {e["id"] % 7}


def leave_days(e, f, t):
    n, d = 0, f
    while d <= t:
        if d.weekday() not in off_days(e) and not (e["lt"] == "office" and d in HOL and HOL[d] in (None, e["state"])): n += 1
        d += timedelta(days=1)
    return n


def run(eng, seed=42, data="data"):
    rng = random.Random(seed + 9)
    T = metadata.tables
    with eng.begin() as c:
        emps = [dict(r._mapping) for r in c.execute(text(
            "select e.id, e.name, e.manager_id, e.join_date, e.location_id, l.type lt, l.state, l.tier, l.name lname, l.city, g.title des, e.department_id from employee e "
            "join location l on l.id=e.location_id join designation g on g.id=e.designation_id order by e.id"))]
        for e in emps: e["join_date"] = d_of(e["join_date"]); e["exit"] = None; e["status"] = "active"
        dept = {r[1]: r[0] for r in c.execute(text("select id, name from department"))}
        desg = {r[1]: r[0] for r in c.execute(text("select id, title from designation"))}
        shift_id = {r[1]: r[0] for r in c.execute(text("select id, code from shift"))}
        ltype = {r[1]: r[0] for r in c.execute(text("select id, code from leave_type"))}
        p = c.execute(text("select params from demo_finding where code='F1'")).scalar()
        hyd = (json.loads(p) if isinstance(p, str) else p)["warehouse_id"]
        hq = c.execute(text("select id from location where type='office' order by id limit 1")).scalar()
        by_loc = {}
        for e in emps: by_loc.setdefault(e["location_id"], []).append(e)
        remain = {k: len(v) for k, v in by_loc.items()}

        # ---- holidays
        c.execute(insert(T["holiday"]), [dict(date=d, name=n, state=s) for d, n, s in HOLIDAYS])

        # ---- exits and notice periods (a store keeps at least 3 people, a warehouse at least 6)
        exited, notice = [], []
        def take(e, kind):
            floor = 3 if e["lt"] == "store" else 6
            if remain[e["location_id"]] <= floor or e["status"] != "active": return False
            remain[e["location_id"]] -= 1
            if kind == "exit": e["status"] = "exited"; e["exit"] = TODAY - timedelta(days=rng.randint(1, 89)); exited.append(e)
            else: e["status"] = "notice"; e["exit"] = TODAY + timedelta(days=rng.randint(3, 28)); notice.append(e)
            e["reason"] = rng.choice(REASONS)
            return True
        hyd_staff = [e for e in by_loc[hyd] if e["des"] == "Warehouse Associate"]
        for e in rng.sample(hyd_staff, 5): take(e, "exit"); e["reason"] = "Shift timings" if rng.random() < .6 else "Better pay elsewhere"
        for e in emps:
            if e["des"] in ("Sales Associate", "Cashier", "Warehouse Associate") and e["join_date"] < TODAY - timedelta(days=120) and e["status"] == "active" and e["location_id"] != hyd:
                r = rng.random()
                if r < .042: take(e, "exit")
                elif r < .060: take(e, "notice")
        for e in exited:
            e["exit"] = max(e["exit"], e["join_date"] + timedelta(days=30))
            if e["exit"] >= TODAY: e["exit"] = TODAY - timedelta(days=1)
        for e in emps:
            if e["join_date"] > TODAY and e["status"] == "active": e["status"] = "joining"
        c.execute(text("update employee set status=:s, exit_date=:d, exit_reason=:r where id=:i"),
                  [dict(s=e["status"], d=e["exit"], r=e.get("reason"), i=e["id"]) for e in emps if e["status"] != "active"])

        # ---- leave
        leave, taken, ranges = [], {}, {}
        def add_leave(e, code, f, t, status, applied, decided=None, note=None):
            days = leave_days(e, f, t)
            if days <= 0: return False
            if any(not (t < a or f > b) for a, b, s in ranges.get(e["id"], []) if s in ("approved", "pending")): return False
            if status in ("approved", "pending") and f.year == 2026 and taken.get((e["id"], code), 0) + days > QUOTA[code]: return False
            if status in ("approved", "pending") and f.year == 2026: taken[(e["id"], code)] = taken.get((e["id"], code), 0) + days
            ranges.setdefault(e["id"], []).append((f, t, status))
            leave.append(dict(employee_id=e["id"], leave_type_id=ltype[code], from_date=f, to_date=t, status=status, is_wfh=code == "WFH", approver_id=e["manager_id"], days=days,
                              reason=rng.choice(["Family function", "Travel", "Not well", "Personal work", "Festival", "Appointment", "Home visit"]) if code != "WFH" else "Work from home",
                              applied_on=applied, decided_on=decided, decision_note=note))
            return True
        jan1 = date(2026, 1, 1)
        for e in emps:
            if e["status"] == "joining": continue
            start = max(jan1, e["join_date"]); last = min(TODAY - timedelta(days=2), e["exit"] or TODAY)
            if (last - start).days < 5: continue
            plan = [("CL", rng.randint(0, 3), 3), ("SL", rng.randint(0, 2), 2), ("EL", rng.randint(0, 2), 5)] + ([("WFH", rng.randint(0, 8), 2)] if e["lt"] == "office" else [])
            for code, n, mx in plan:
                for _ in range(n):
                    dur = rng.randint(1, mx); f = start + timedelta(days=rng.randint(0, max(0, (last - start).days - dur))); t = f + timedelta(days=dur - 1)
                    r = rng.random(); st = "approved" if r < .90 else "rejected" if r < .96 else "cancelled"
                    ap = min(f - timedelta(days=rng.randint(1, 10)), TODAY - timedelta(days=1))
                    add_leave(e, code, f, t, st, ap, ap + timedelta(days=rng.randint(0, 2)), "Not possible in the festival week" if st == "rejected" else None)
        live = [e for e in emps if e["status"] in ("active", "notice") and e["manager_id"]]
        nxt = {"approved": 0, "pending": 0}
        for e in rng.sample(live, len(live)):
            if nxt["approved"] >= 40 and nxt["pending"] >= 70: break
            st = "approved" if nxt["approved"] < 40 else "pending"
            if st == "pending" and nxt["pending"] >= 70: continue
            if e["exit"] and e["exit"] < TODAY + timedelta(days=30): continue
            f = TODAY + timedelta(days=rng.randint(4, 25)); t = f + timedelta(days=rng.randint(0, 2))
            ap = TODAY - timedelta(days=(rng.randint(4, 8) if st == "pending" and nxt["pending"] < 14 else rng.randint(0, 3)))
            if add_leave(e, rng.choice(["CL", "EL"] if e["lt"] != "office" else ["CL", "EL", "WFH"]), f, t, st, ap, ap if st == "approved" else None): nxt[st] += 1
        # planted: pending leave on 3 Nov in three small stores
        D = TODAY + timedelta(days=3); planted = []
        tierc = [l for l, v in by_loc.items() if v[0]["lt"] == "store" and v[0]["tier"] == "C" and remain[l] == len(v) and all(x["status"] == "active" for x in v)]
        for loc in rng.sample(tierc, 3):
            wk = [x for x in by_loc[loc] if D.weekday() not in off_days(x) and not any(a <= D <= b for a, b, s in ranges.get(x["id"], []))]
            if len(wk) < 2: continue
            made = 0
            for x in wk[:len(wk) - 1][:2]:
                if add_leave(x, "CL", D, D, "pending", TODAY - timedelta(days=1)): made += 1
            if made: planted.append(loc)
        c.execute(insert(T["leave_request"]), leave)
        appr = {}
        for lv in leave:
            if lv["status"] == "approved":
                d = lv["from_date"]
                while d <= lv["to_date"]: appr.setdefault(lv["employee_id"], set()).add(d); d += timedelta(days=1)

        # ---- rosters and attendance
        ros, att, a_stat = [], [], {}
        mon0 = ATT_START - timedelta(days=ATT_START.weekday()); ntot = (ROSTER_END - ATT_START).days + 1
        for e in emps:
            if e["status"] == "joining" and e["join_date"] > ROSTER_END: continue
            lt, off = e["lt"], off_days(e)
            for i in range(ntot):
                d = ATT_START + timedelta(days=i)
                if d < e["join_date"] or (e["exit"] and d > e["exit"]) or d.weekday() in off: continue
                if lt == "office" and d in HOL and HOL[d] in (None, e["state"]): continue
                sh = "GENERAL" if lt != "store" else "MORNING" if e["des"] == "Store Manager" else ("MORNING" if ((d - mon0).days // 7 + e["id"]) % 2 == 0 else "EVENING")
                ros.append(dict(employee_id=e["id"], date=d, shift_id=shift_id[sh], location_id=e["location_id"]))
                if d >= TODAY: continue
                if d in appr.get(e["id"], ()): att.append(dict(employee_id=e["id"], date=d, punch_in=None, punch_out=None, source="system", location_id=e["location_id"], hours=None, status="L", fixed=False)); continue
                pa = .13 if e["location_id"] == hyd else .03 if lt == "store" else .02
                if rng.random() < pa: att.append(dict(employee_id=e["id"], date=d, punch_in=None, punch_out=None, source="system", location_id=e["location_id"], hours=None, status="A", fixed=False)); continue
                s0, s1 = SHIFTS[sh]; base = datetime.combine(d, datetime.min.time())
                st0 = base + timedelta(hours=int(s0[:2]), minutes=int(s0[3:])); st1 = base + timedelta(hours=int(s1[:2]), minutes=int(s1[3:]))
                pin = st0 + timedelta(minutes=rng.randint(16, 55) if rng.random() < .07 else int(rng.gauss(-2, 5)))
                src = "biometric" if lt != "store" else ("pos_login" if rng.random() < .9 else "app")
                r = rng.random()
                if r < .006:
                    fx = d < TODAY - timedelta(days=7) and rng.random() < .6
                    pout = st1 + timedelta(minutes=int(rng.gauss(5, 12))) if fx else None
                    att.append(dict(employee_id=e["id"], date=d, punch_in=pin, punch_out=pout, source=src, location_id=e["location_id"], hours=round(((pout - pin).total_seconds() / 3600) - 1, 2) if fx else None, status="P" if fx else "M", fixed=fx))
                elif r < .016:
                    pout = pin + timedelta(hours=4, minutes=rng.randint(0, 25)); att.append(dict(employee_id=e["id"], date=d, punch_in=pin, punch_out=pout, source=src, location_id=e["location_id"], hours=round((pout - pin).total_seconds() / 3600, 2), status="H", fixed=False))
                else:
                    pout = st1 + timedelta(minutes=int(rng.gauss(5, 12))); att.append(dict(employee_id=e["id"], date=d, punch_in=pin, punch_out=pout, source=src, location_id=e["location_id"], hours=round((pout - pin).total_seconds() / 3600 - 1, 2), status="P", fixed=False))
        for i in range(0, len(ros), 20000): c.execute(insert(T["roster"]), ros[i:i + 20000])
        for i in range(0, len(att), 20000): c.execute(insert(T["attendance"]), att[i:i + 20000])

        # ---- onboarding tasks (joined in the last 45 days or joining in the next 60)
        ob = []
        for e in emps:
            if TODAY - timedelta(days=45) <= e["join_date"] <= TODAY + timedelta(days=60):
                for k, (t, off_) in enumerate(TASKS):
                    due = e["join_date"] + timedelta(days=off_)
                    if due < TODAY: done = rng.random() < (.97 if k < 4 else .8)
                    else: done = e["join_date"] > TODAY and k < 2 and rng.random() < .6
                    ob.append(dict(employee_id=e["id"], task=t, due_date=due, done_at=datetime.combine(min(due, TODAY - timedelta(days=1)) - timedelta(days=rng.randint(0, 2)), datetime.min.time()) + timedelta(hours=11) if done else None))
        c.execute(insert(T["onboarding_task"]), ob)

        # ---- recruitment
        jobs, apps = [], []
        stores = [e for e in emps if e["des"] == "Store Manager"]
        spec = [("Warehouse Associate", "Supply Chain", hyd, 5, "open")]
        for s in rng.sample(stores, 14): spec.append((rng.choice(["Sales Associate", "Cashier"]), "Retail Operations", s["location_id"], rng.randint(1, 2), "open"))
        for t, dp in [("Category Analyst", "Marketing"), ("Accounts Executive", "Finance"), ("Data Engineer", "IT and Analytics"), ("Procurement Executive", "Procurement"), ("HR Executive", "HR"), ("Logistics Planner", "Supply Chain"), ("Finance Manager", "Finance"), ("Backend Developer", "IT and Analytics")]:
            spec.append((t, dp, hq, 1, "open"))
        for t, dp, loc in [("Sales Associate", "Retail Operations", stores[3]["location_id"]), ("Cashier", "Retail Operations", stores[9]["location_id"]), ("Marketing Executive", "Marketing", hq)]: spec.append((t, dp, loc, 1, "closed"))
        lname = {e["location_id"]: e["lname"] for e in emps}
        for j, (title, dp, loc, n, st) in enumerate(spec):
            des = desg.get(title, desg["Executive"] if dp not in ("Retail Operations", "Supply Chain") else desg["Sales Associate"])
            posted = TODAY - timedelta(days=rng.randint(3, 40)); at = f" at {lname[loc]}" if loc != hq else ""
            jobs.append(dict(id=j + 1, title=f"{title}{at}", department_id=dept[dp], location_id=loc, status=st, posted_on=posted, closes_on=posted + timedelta(days=45), designation_id=des, openings=n,
                             description=f"{title} for the {dp} team{at}. Full time. Salary is discussed after the first interview."))
            if st == "closed": want = [("Hired", n)] + [("Rejected", rng.randint(2, 5))]
            elif loc == hyd: want = [("Applied", 1), ("Screen", 1)]
            else:
                h = 1 if n > 1 and rng.random() < .35 else 0
                want = [("Applied", rng.randint(2, 8)), ("Screen", rng.randint(1, 5)), ("Interview", rng.randint(0, 4)), ("Offer", rng.randint(0, 1)), ("Hired", h), ("Rejected", rng.randint(1, 6))]
            for stg, cnt in want:
                for _ in range(cnt):
                    f, l = rng.choice(N.FIRST), rng.choice(N.LAST); ap = posted + timedelta(days=rng.randint(0, max(0, (TODAY - posted).days)))
                    apps.append(dict(job_id=j + 1, name=f"{f} {l}", stage=stg, applied_on=ap, source=rng.choice(SOURCES), email=f"{f}.{l}.{len(apps) + 1}@applicant.invalid".lower(), stage_changed_on=min(TODAY, ap + timedelta(days=rng.randint(0, 6))), employee_id=None))
        c.execute(insert(T["job_posting"]), jobs); c.execute(insert(T["applicant"]), apps)
        c.execute(insert(T["demo_finding"]), [dict(code="F9", module="people", title="Warehouse losing people", description="Hyderabad warehouse lost 5 associates in 90 days, runs about 11 percent absence and has two applicants for five openings (seeded in the HR module).",
                                                  params=dict(warehouse_id=hyd, planted_leave_stores=planted))])
    return dict(exited=len(exited), notice=len(notice), roster=len(ros), attendance=len(att), leave=len(leave), onboarding=len(ob), jobs=len(jobs), applicants=len(apps), planted_stores=len(planted))
