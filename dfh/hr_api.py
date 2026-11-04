"""Module 9 API: people. Directory, org chart, attendance and regularisation, rosters, leave with coverage checks, onboarding, recruitment into hiring, celebrations, exits, and a public careers feed.
There is no payroll, no salary data and no statutory filing here. Punches are simulated (biometric for office and warehouse, POS login for stores). Rules below are stated assumptions."""
import re
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text

HR = {"ceo", "hr", "admin"}                       # full access
MGR = {"store_manager", "warehouse"}              # own store or warehouse only
SHIFT_PAID = {"MORNING": 7.0, "EVENING": 7.5, "GENERAL": 8.0}      # shift span minus a 1 hour break
SHIFT_TIME = {"MORNING": ("09:00", "17:00"), "EVENING": ("13:00", "21:30"), "GENERAL": ("09:30", "18:30")}
MIN_COVER = {"store": 2, "warehouse": 5}          # people on shift
MAX_DAYS_WEEK, MAX_HOURS_WEEK, MIN_REST_H = 6, 48, 11
FIX_DAYS = {"hr": 30, "ceo": 30, "admin": 30, "store_manager": 7, "warehouse": 7}
LATE_MIN, LONG_LEAVE, BACKDATE_DAYS, NOTICE_DAYS, AGED_LEAVE_DAYS = 15, 5, 7, 30, 3
STD_STAFF = {"A": 6, "B": 4, "C": 3}              # store manager, cashier and sales associates (matches the seeded layout)
NEXT = {"Applied": ["Screen", "Rejected"], "Screen": ["Interview", "Rejected"], "Interview": ["Offer", "Rejected"], "Offer": ["Hired", "Rejected"], "Hired": [], "Rejected": []}
TASKS = [("Offer letter signed", -3), ("ID and bank details submitted", -2), ("System login created", 0), ("Uniform and ID card issued", 1), ("Induction with manager", 3), ("Role training signed off", 10)]
MAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
HM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class FixIn(BaseModel):
    employee_id: int
    date: str
    punch_in: Optional[str] = None
    punch_out: str
    reason: str


class RosterIn(BaseModel):
    employee_id: int
    date: str
    shift: Optional[str] = None


class CopyIn(BaseModel):
    location_id: int
    week: str


class LeaveIn(BaseModel):
    employee_id: int
    type: str
    from_date: str
    to_date: str
    reason: Optional[str] = None


class DecideIn(BaseModel):
    action: str
    note: Optional[str] = None
    force: bool = False


class ExitIn(BaseModel):
    action: str
    last_day: Optional[str] = None
    reason: Optional[str] = None


class DoneIn(BaseModel):
    done: bool


class JobIn(BaseModel):
    title: str
    department_id: int
    designation_id: int
    location_id: Optional[int] = None
    openings: int = 1
    closes_on: Optional[str] = None
    description: Optional[str] = None


class AppIn(BaseModel):
    job_id: int
    name: str
    email: str
    source: str = "Referral"


class StageIn(BaseModel):
    stage: str
    birth_date: Optional[str] = None
    join_date: Optional[str] = None


class ApplyIn(BaseModel):
    name: str
    email: str


def attach(app, ctx):
    me, need, many, one, audit, engine, NOW = (ctx[k] for k in ("me", "need", "many", "one", "audit", "engine", "NOW"))
    TODAY = NOW.date()
    allr, hrr = need(HR | MGR), need(HR)

    def parse(s, what="Date"):
        try: return date.fromisoformat(str(s)[:10])
        except Exception: raise HTTPException(400, f"{what} must look like 2026-11-03")

    def dt(x): return x if isinstance(x, datetime) else datetime.fromisoformat(str(x))

    def is_hr(u): return u["role"] in HR

    def scope_loc(u): return u["scope_id"] if u["role"] in MGR and u["scope_type"] in ("store", "warehouse") else None

    def emp_or_404(eid, u):
        e = one("select e.*, l.type lt, l.state, l.name lname, l.city, l.tier, g.title des, d.name dept from employee e join location l on l.id=e.location_id join designation g on g.id=e.designation_id join department d on d.id=e.department_id where e.id=:i", i=eid)
        sl = scope_loc(u)
        if not e or (u["role"] not in HR and (sl is None or e["location_id"] != sl)): raise HTTPException(404, "Employee not found")
        return e

    def need_loc(u, loc):
        sl = scope_loc(u)
        if u["role"] not in HR and loc != sl: raise HTTPException(403, "You can only work on your own location")
        l = one("select id, name, type, city from location where id=:i", i=loc)
        if not l: raise HTTPException(404, "Location not found")
        return l

    def pager(page, size): return max(1, page), max(5, min(size, 100))

    def holidays(): return {parse(r["date"]): r["state"] for r in many("select date, state from holiday")}

    def off_days(e): return {5, 6} if e["lt"] == "office" else {e["id"] % 7}

    def leave_days(e, f, t, hol=None):
        hol = holidays() if hol is None else hol; n, d = 0, f
        while d <= t:
            if d.weekday() not in off_days(e) and not (e["lt"] == "office" and d in hol and hol[d] in (None, e["state"])): n += 1
            d += timedelta(days=1)
        return n

    def balances(e, year):
        rows = many("select lt.code, lt.name, lt.annual_quota q, coalesce(sum(case when lr.status='approved' then lr.days end),0) used, coalesce(sum(case when lr.status='pending' then lr.days end),0) pending "
                    "from leave_type lt left join leave_request lr on lr.leave_type_id=lt.id and lr.employee_id=:e and lr.from_date>=:a and lr.from_date<=:b group by lt.id order by lt.id", e=e["id"], a=f"{year}-01-01", b=f"{year}-12-31")
        return [dict(r, left=r["q"] - r["used"] - r["pending"]) for r in rows if e["lt"] == "office" or r["code"] != "WFH"]

    def on_leave(loc, d, skip=None):
        return {r["employee_id"] for r in many("select lv.employee_id from leave_request lv join employee e on e.id=lv.employee_id where e.location_id=:l and lv.status='approved' and lv.from_date<=:d and lv.to_date>=:d and lv.id!=:s", l=loc, d=str(d), s=skip or -1)}

    def cover(loc, d, skip=None):
        rost = {r["employee_id"] for r in many("select employee_id from roster where location_id=:l and date=:d", l=loc, d=str(d))}
        return len(rost - on_leave(loc, d, skip)), rost

    def week_of(d): return d - timedelta(days=d.weekday())

    def mask(rows, u, keys=("email", "birth_date")):
        if u["role"] in HR: return rows
        for r in rows:
            for k in keys: r.pop(k, None)
        return rows

    # ---------------- options ----------------
    @app.get("/api/hr/options")
    def options(u=Depends(allr)):
        sl = scope_loc(u)
        locs = many("select id, name, city, type from location where type in ('store','warehouse') and (:s is null or id=:s) order by type desc, city, name", s=sl)
        return dict(is_hr=is_hr(u), scope=sl, asof=str(NOW), today=str(TODAY), shifts=[dict(code=k, start=v[0], end=v[1], paid=SHIFT_PAID[k]) for k, v in SHIFT_TIME.items()],
                    leave_types=many("select code, name, annual_quota q from leave_type order by id"), locations=locs, stages=list(NEXT), fix_days=FIX_DAYS[u["role"]],
                    departments=many("select id, name from department order by name") if is_hr(u) else [], designations=many("select id, title from designation order by level desc") if is_hr(u) else [],
                    assumptions=dict(cover=f"Stores need {MIN_COVER['store']} people on shift, warehouses {MIN_COVER['warehouse']}", week=f"At most {MAX_DAYS_WEEK} days and {MAX_HOURS_WEEK} paid hours a week, {MIN_REST_H} hours rest between shifts",
                                     late=f"Late means more than {LATE_MIN} minutes after shift start", fix=f"Missing punches can be fixed within {FIX_DAYS[u['role']]} days by your role",
                                     leave=f"Leave above {LONG_LEAVE} days needs HR. Notice period is {NOTICE_DAYS} days. Holiday dates marked assumed are not confirmed",
                                     scope="No payroll or salary data. Punches are simulated."))

    # ---------------- summary ----------------
    @app.get("/api/hr/summary")
    def summary(u=Depends(allr)):
        sl = scope_loc(u); wl = " and location_id=:l" if sl else ""; el = " and e.location_id=:l" if sl else ""; y = TODAY - timedelta(days=1)
        hc = many("select l.type, e.status, count(*) n from employee e join location l on l.id=e.location_id where 1=1" + el + " group by 1,2", l=sl)
        on_roll = sum(r["n"] for r in hc if r["status"] in ("active", "notice")); notice = sum(r["n"] for r in hc if r["status"] == "notice")
        joining = sum(r["n"] for r in hc if r["status"] == "joining"); exits90 = sum(r["n"] for r in hc if r["status"] == "exited")
        a = one("select count(*) n, sum(case when status in ('P','H','M') then 1 else 0 end) pres, sum(case when status='A' then 1 else 0 end) ab, sum(case when status='L' then 1 else 0 end) lv from attendance where date=:d" + wl, d=str(y), l=sl)
        late = one("select count(*) n from attendance a join roster r on r.employee_id=a.employee_id and r.date=a.date join shift s on s.id=r.shift_id where a.date=:d and a.punch_in is not null and time(a.punch_in) > time(s.start_time, '+%d minutes')" % LATE_MIN + wl.replace("location_id", "a.location_id"), d=str(y), l=sl)["n"]
        sched = a["n"] - (a["lv"] or 0)
        trend = many("select date, sum(case when status in ('P','H','M') then 1 else 0 end)*1.0/nullif(sum(case when status!='L' then 1 else 0 end),0) pct from attendance where date>=:a and date<=:b" + wl + " group by date order by date", a=str(TODAY - timedelta(days=14)), b=str(y), l=sl)
        worst = many("select l.id, l.name, l.city, l.type, sum(case when a.status in ('P','H','M') then 1 else 0 end)*1.0/sum(case when a.status!='L' then 1 else 0 end) pct, count(*) n from attendance a join location l on l.id=a.location_id "
                     "where a.date>=:a and a.date<=:b" + wl.replace("location_id", "a.location_id") + " group by l.id having count(*)>=60 order by pct limit 8", a=str(TODAY - timedelta(days=14)), b=str(y), l=sl) if sl is None else []
        lv = one("select count(*) n, sum(case when lr.applied_on<=:t then 1 else 0 end) aged from leave_request lr join employee e on e.id=lr.employee_id where lr.status='pending'" + el, t=str(TODAY - timedelta(days=AGED_LEAVE_DAYS)), l=sl)
        mp = one("select count(*) n from attendance where status='M' and date>=:a" + wl, a=str(TODAY - timedelta(days=30)), l=sl)["n"]
        gaps = one("select count(*) n from (select r.location_id, r.date from roster r join location l on l.id=r.location_id where l.type='store' and r.date>=:a and r.date<=:b" + wl.replace("location_id", "r.location_id") +
                   " and r.employee_id not in (select lv.employee_id from leave_request lv where lv.status='approved' and lv.from_date<=r.date and lv.to_date>=r.date) group by r.location_id, r.date having count(*)<%d)" % MIN_COVER["store"], a=str(TODAY), b=str(TODAY + timedelta(days=6)), l=sl)["n"]
        res = dict(headcount=on_roll, notice=notice, joining=joining, exits90=exits90, attrition=(exits90 / max(on_roll, 1) * 4) if exits90 else 0.0, by_type=[dict(type=t, n=sum(r["n"] for r in hc if r["type"] == t and r["status"] in ("active", "notice"))) for t in ("office", "store", "warehouse")],
                   att_date=str(y), att=dict(scheduled=sched, present=a["pres"] or 0, absent=a["ab"] or 0, leave=a["lv"] or 0, late=late, pct=(a["pres"] or 0) / sched if sched else None),
                   trend=[dict(date=r["date"], pct=r["pct"]) for r in trend], worst=worst, leave_pending=lv["n"], leave_aged=lv["aged"] or 0, missing_punch=mp, cover_gaps=gaps)
        if is_hr(u):
            res["vacancies"] = one("select coalesce(sum(j.openings - (select count(*) from applicant p where p.job_id=j.id and p.stage='Hired')),0) n from job_posting j where j.status='open'")["n"]
            res["exit_hot"] = many("select l.id, l.name, l.type, count(*) n from employee e join location l on l.id=e.location_id where e.status='exited' group by l.id order by n desc limit 5")
        return res

    # ---------------- directory ----------------
    @app.get("/api/hr/employees")
    def employees(q: str = "", location_id: int = 0, dept_id: int = 0, status: str = "", lt: str = "", page: int = 1, size: int = 25, u=Depends(allr)):
        page, size = pager(page, size); sl = scope_loc(u)
        w, p = "", dict(n=size, o=(page - 1) * size)
        if sl: w += " and e.location_id=:sl"; p["sl"] = sl
        if location_id: w += " and e.location_id=:loc"; p["loc"] = location_id
        if dept_id: w += " and e.department_id=:dp"; p["dp"] = dept_id
        if lt in ("office", "store", "warehouse"): w += " and l.type=:lt"; p["lt"] = lt
        if q: w += " and (lower(e.name) like :q or lower(e.emp_code) like :q)"; p["q"] = f"%{q.lower()}%"
        w += " and e.status=:st" if status else " and e.status in ('active','notice','joining')"
        if status: p["st"] = status
        base = "from employee e join department d on d.id=e.department_id join designation g on g.id=e.designation_id join location l on l.id=e.location_id left join employee m on m.id=e.manager_id where 1=1" + w
        rows = many("select e.id, e.emp_code, e.name, e.status, e.join_date, e.exit_date, d.name dept, g.title des, l.name loc, l.city, l.type lt, m.name manager, e.email " + base + " order by e.name limit :n offset :o", **p)
        return dict(total=one("select count(*) n " + base, **p)["n"], rows=mask(rows, u))

    @app.get("/api/hr/employees/{eid}")
    def employee(eid: int, u=Depends(allr)):
        e = emp_or_404(eid, u)
        mgr = one("select e.id, e.name, g.title des from employee e join designation g on g.id=e.designation_id where e.id=:i", i=e["manager_id"]) if e["manager_id"] else None
        reports = one("select count(*) n from employee where manager_id=:i and status in ('active','notice')", i=eid)["n"]
        a30 = many("select status, count(*) n from attendance where employee_id=:e and date>=:a group by status", e=eid, a=str(TODAY - timedelta(days=30)))
        last = many("select a.date, a.status, a.punch_in, a.punch_out, a.hours, a.fixed from attendance a where a.employee_id=:e order by a.date desc limit 14", e=eid)
        nxt = many("select r.date, s.code from roster r join shift s on s.id=r.shift_id where r.employee_id=:e and r.date>=:a and r.date<=:b order by r.date", e=eid, a=str(TODAY), b=str(TODAY + timedelta(days=6)))
        lv = many("select lr.id, t.code, lr.from_date, lr.to_date, lr.days, lr.status from leave_request lr join leave_type t on t.id=lr.leave_type_id where lr.employee_id=:e order by lr.from_date desc limit 8", e=eid)
        ob = many("select id, task, due_date, done_at from onboarding_task where employee_id=:e order by due_date", e=eid)
        prof = {k: e[k] for k in ("id", "emp_code", "name", "status", "join_date", "exit_date", "exit_reason", "dept", "des", "lname", "city", "lt", "location_id", "email", "birth_date")}
        mask([prof], u)
        return dict(profile=prof, manager=mgr, reports=reports, balances=balances(e, TODAY.year), att30={r["status"]: r["n"] for r in a30}, attendance=last, roster=nxt, leave=lv, onboarding=ob)

    @app.post("/api/hr/employees/{eid}/exit")
    def exit_flow(eid: int, b: ExitIn, u=Depends(hrr)):
        e = emp_or_404(eid, u)
        with engine.begin() as c:
            if b.action == "resign":
                if e["status"] != "active": raise HTTPException(409, "Only an active employee can be put on notice")
                ld = parse(b.last_day, "Last day")
                if ld < TODAY: raise HTTPException(400, "Last day cannot be in the past")
                if (ld - TODAY).days < NOTICE_DAYS and u["role"] not in ("ceo", "admin"): raise HTTPException(403, f"Notice shorter than {NOTICE_DAYS} days needs the CEO or admin")
                if not (b.reason or "").strip(): raise HTTPException(400, "Add a reason")
                c.execute(text("update employee set status='notice', exit_date=:d, exit_reason=:r where id=:i"), dict(d=ld, r=b.reason.strip()[:40], i=eid))
                c.execute(text("delete from roster where employee_id=:i and date>:d"), dict(i=eid, d=ld))
                c.execute(text("update leave_request set status='cancelled', decision_note='Cancelled: employee leaves before these dates' where employee_id=:i and status='pending' and from_date>:d"), dict(i=eid, d=ld))
                audit(c, u, "hr.exit.resign", "employee", eid, dict(status=e["status"]), dict(status="notice", last_day=str(ld), reason=b.reason))
            elif b.action == "withdraw":
                if e["status"] != "notice": raise HTTPException(409, "Not on notice")
                c.execute(text("update employee set status='active', exit_date=null, exit_reason=null where id=:i"), dict(i=eid))
                audit(c, u, "hr.exit.withdraw", "employee", eid, dict(status="notice", last_day=str(e["exit_date"])), dict(status="active"))
            elif b.action == "complete":
                if e["status"] != "notice" or parse(e["exit_date"]) > TODAY: raise HTTPException(409, "The last day has not passed yet")
                c.execute(text("update employee set status='exited' where id=:i"), dict(i=eid))
                c.execute(text("update leave_request set status='cancelled', decision_note='Employee has left' where employee_id=:i and status='pending'"), dict(i=eid))
                audit(c, u, "hr.exit.complete", "employee", eid, dict(status="notice"), dict(status="exited"))
            else: raise HTTPException(400, "Action must be resign, withdraw or complete")
        return one("select id, status, exit_date from employee where id=:i", i=eid)

    # ---------------- org and headcount ----------------
    @app.get("/api/hr/org")
    def org(id: int = 0, u=Depends(hrr)):
        root = one("select e.id, e.name, g.title des, d.name dept, l.name loc from employee e join designation g on g.id=e.designation_id join department d on d.id=e.department_id join location l on l.id=e.location_id where e.id=:i", i=id) if id else \
            one("select e.id, e.name, g.title des, d.name dept, l.name loc from employee e join designation g on g.id=e.designation_id join department d on d.id=e.department_id join location l on l.id=e.location_id where e.manager_id is null order by e.id limit 1")
        if not root: raise HTTPException(404, "Employee not found")
        chain, m = [], one("select manager_id from employee where id=:i", i=root["id"])["manager_id"]
        while m and len(chain) < 6:
            r = one("select e.id, e.name, g.title des, e.manager_id from employee e join designation g on g.id=e.designation_id where e.id=:i", i=m); chain.insert(0, dict(id=r["id"], name=r["name"], des=r["des"])); m = r["manager_id"]
        tot = one("select count(*) n from employee where manager_id=:i and status in ('active','notice')", i=root["id"])["n"]
        reps = many("select e.id, e.name, g.title des, l.name loc, (select count(*) from employee r where r.manager_id=e.id and r.status in ('active','notice')) n from employee e join designation g on g.id=e.designation_id join location l on l.id=e.location_id "
                    "where e.manager_id=:i and e.status in ('active','notice') order by n desc, e.name limit 60", i=root["id"])
        return dict(node=root, chain=chain, reports=reps, total=tot)

    @app.get("/api/hr/headcount")
    def headcount(u=Depends(hrr)):
        mat = many("select d.name dept, l.type, count(*) n from employee e join department d on d.id=e.department_id join location l on l.id=e.location_id where e.status in ('active','notice') group by 1,2 order by d.name")
        short = many("select l.id, l.name, l.city, l.tier, sum(case when e.status='active' then 1 else 0 end) active, sum(case when e.status='notice' then 1 else 0 end) notice from location l join employee e on e.location_id=l.id "
                     "where l.type='store' and e.status in ('active','notice') group by l.id")
        out = []
        for r in short:
            std = STD_STAFF.get(r["tier"], 3); gap = std - r["active"]
            if gap > 0 or r["notice"]: out.append(dict(r, standard=std, gap=max(gap, 0), after_notice=std - r["active"]))
        out.sort(key=lambda r: (-r["after_notice"], -r["notice"]))
        wh = many("select l.id, l.name, l.city, sum(case when e.status in ('active','notice') then 1 else 0 end) staff, sum(case when e.status='exited' then 1 else 0 end) exits90, sum(case when e.status='notice' then 1 else 0 end) notice from location l join employee e on e.location_id=l.id where l.type='warehouse' group by l.id order by exits90 desc")
        return dict(matrix=mat, stores=out[:40], stores_total=len(out), warehouses=[dict(w, exit_pct=w["exits90"] / max(w["staff"] + w["exits90"], 1)) for w in wh],
                    note=f"Store standard is {STD_STAFF['A']}, {STD_STAFF['B']} and {STD_STAFF['C']} people for tiers A, B and C (assumed). Warehouses have no stated standard, so exits over 90 days are shown instead.")

    # ---------------- attendance ----------------
    @app.get("/api/hr/attendance")
    def attendance(date_: str = "", location_id: int = 0, status: str = "", q: str = "", page: int = 1, size: int = 30, u=Depends(allr)):
        page, size = pager(page, size); d = parse(date_) if date_ else TODAY - timedelta(days=1); sl = scope_loc(u)
        loc = sl or (location_id or None); w, p = "", dict(d=str(d), n=size, o=(page - 1) * size)
        if loc: w += " and a.location_id=:l"; p["l"] = loc
        if q: w += " and (lower(e.name) like :q or lower(e.emp_code) like :q)"; p["q"] = f"%{q.lower()}%"
        base = "from attendance a join employee e on e.id=a.employee_id join designation g on g.id=e.designation_id left join roster r on r.employee_id=a.employee_id and r.date=a.date left join shift s on s.id=r.shift_id where a.date=:d" + w
        cnt = {r["status"]: r["n"] for r in many("select a.status, count(*) n " + base + " group by a.status", **p)}
        if status in ("P", "A", "L", "H", "M", "late"):
            if status == "late": w2 = " and a.punch_in is not null and time(a.punch_in) > time(s.start_time, '+%d minutes')" % LATE_MIN
            else: w2 = " and a.status=:st"; p["st"] = status
        else: w2 = ""
        rows = many("select a.employee_id, e.emp_code, e.name, g.title des, a.status, a.punch_in, a.punch_out, a.hours, a.fixed, a.source, s.code shift, s.start_time, a.location_id " + base + w2 +
                    " order by case a.status when 'M' then 0 when 'A' then 1 else 2 end, e.name limit :n offset :o", **p)
        win = FIX_DAYS[u["role"]]
        for r in rows:
            r["late"] = bool(r["punch_in"] and r["start_time"] and dt(r["punch_in"]).strftime("%H:%M") > (datetime.strptime(r["start_time"], "%H:%M") + timedelta(minutes=LATE_MIN)).strftime("%H:%M"))
            r["can_fix"] = r["status"] == "M" and (TODAY - d).days <= win or (r["status"] == "A" and is_hr(u) and (TODAY - d).days <= win)
        return dict(date=str(d), counts=cnt, total=one("select count(*) n " + base + w2, **p)["n"], rows=rows)

    @app.post("/api/hr/attendance/fix")
    def fix(b: FixIn, u=Depends(allr)):
        e = emp_or_404(b.employee_id, u); d = parse(b.date)
        r = one("select * from attendance where employee_id=:e and date=:d", e=b.employee_id, d=str(d))
        if not r: raise HTTPException(404, "No attendance row for that day")
        if r["status"] not in ("M", "A"): raise HTTPException(409, "Only missing punches or absences can be corrected")
        if r["status"] == "A" and not is_hr(u): raise HTTPException(403, "Only HR can turn an absence into a present day")
        if (TODAY - d).days > FIX_DAYS[u["role"]]: raise HTTPException(409, f"Too old for your role. You can fix up to {FIX_DAYS[u['role']]} days back")
        if len((b.reason or "").strip()) < 5: raise HTTPException(400, "Give a reason of at least 5 characters")
        if not HM.match(b.punch_out or ""): raise HTTPException(400, "Punch out must look like 18:30")
        if b.punch_in and not HM.match(b.punch_in): raise HTTPException(400, "Punch in must look like 09:30")
        if r["status"] == "A" and not b.punch_in: raise HTTPException(400, "Punch in is needed to mark an absent day as present")
        pin = datetime.combine(d, datetime.strptime(b.punch_in, "%H:%M").time()) if b.punch_in else dt(r["punch_in"])
        pout = datetime.combine(d, datetime.strptime(b.punch_out, "%H:%M").time())
        span = (pout - pin).total_seconds() / 3600
        if span <= 0 or span > 14: raise HTTPException(400, "Punch out must be after punch in and within 14 hours")
        hours = round(span - 1 if span >= 6 else span, 2); st = "H" if hours < 5 else "P"
        with engine.begin() as c:
            c.execute(text("update attendance set punch_in=:i, punch_out=:o, hours=:h, status=:s, fixed=1 where employee_id=:e and date=:d"), dict(i=pin, o=pout, h=hours, s=st, e=b.employee_id, d=d))
            audit(c, u, "hr.attendance.fix", "attendance", f"{b.employee_id}:{d}", dict(status=r["status"], punch_out=str(r["punch_out"])), dict(status=st, punch_in=str(pin), punch_out=str(pout), reason=b.reason.strip()))
        return dict(status=st, hours=hours)

    # ---------------- rosters ----------------
    def roster_checks(e, d, shift, hrs_week=None):
        """Validate a shift for one employee and day. Returns nothing or raises 400 or 409."""
        if d < TODAY: raise HTTPException(400, "Past days are locked")
        if parse(e["join_date"]) > d or (e["exit_date"] and d > parse(e["exit_date"])) or e["status"] == "exited": raise HTTPException(400, "Employee is not employed on that day")
        allowed = {"MORNING", "EVENING"} if e["lt"] == "store" else {"GENERAL"}
        if shift not in allowed: raise HTTPException(400, f"{e['lt'].title()} staff work {' or '.join(sorted(allowed))} shifts")
        if one("select id from leave_request where employee_id=:e and status='approved' and from_date<=:d and to_date>=:d", e=e["id"], d=str(d)): raise HTTPException(409, "Approved leave on that day")
        mon = week_of(d)
        rows = many("select r.date, s.code from roster r join shift s on s.id=r.shift_id where r.employee_id=:e and r.date>=:a and r.date<=:b and r.date!=:d", e=e["id"], a=str(mon - timedelta(days=1)), b=str(mon + timedelta(days=7)), d=str(d))
        wk = [(parse(r["date"]), r["code"]) for r in rows if mon <= parse(r["date"]) <= mon + timedelta(days=6)]
        if len(wk) + 1 > MAX_DAYS_WEEK: raise HTTPException(409, f"That would be more than {MAX_DAYS_WEEK} working days in the week")
        if sum(SHIFT_PAID[c] for _, c in wk) + SHIFT_PAID[shift] > MAX_HOURS_WEEK: raise HTTPException(409, f"That would be more than {MAX_HOURS_WEEK} paid hours in the week")
        by = {x[0]: x[1] for x in [(parse(r["date"]), r["code"]) for r in rows]}
        st = datetime.combine(d, datetime.strptime(SHIFT_TIME[shift][0], "%H:%M").time()); en = datetime.combine(d, datetime.strptime(SHIFT_TIME[shift][1], "%H:%M").time())
        if d - timedelta(days=1) in by:
            pe = datetime.combine(d - timedelta(days=1), datetime.strptime(SHIFT_TIME[by[d - timedelta(days=1)]][1], "%H:%M").time())
            if (st - pe).total_seconds() / 3600 < MIN_REST_H: raise HTTPException(409, f"Less than {MIN_REST_H} hours rest after the previous day's shift")
        if d + timedelta(days=1) in by:
            ns = datetime.combine(d + timedelta(days=1), datetime.strptime(SHIFT_TIME[by[d + timedelta(days=1)]][0], "%H:%M").time())
            if (ns - en).total_seconds() / 3600 < MIN_REST_H: raise HTTPException(409, f"Less than {MIN_REST_H} hours rest before the next day's shift")

    @app.get("/api/hr/roster")
    def roster(location_id: int, week: str = "", u=Depends(allr)):
        need_loc(u, location_id); mon = week_of(parse(week) if week else TODAY); sun = mon + timedelta(days=6)
        staff = many("select e.id, e.name, e.emp_code, e.status, e.join_date, e.exit_date, g.title des, g.level from employee e join designation g on g.id=e.designation_id where e.location_id=:l and e.status in ('active','notice','exited','joining') "
                     "and e.join_date<=:b and (e.exit_date is null or e.exit_date>=:a) order by g.level desc, e.name", l=location_id, a=str(mon), b=str(sun))
        cells = {(r["employee_id"], r["date"]): r["code"] for r in many("select r.employee_id, r.date, s.code from roster r join shift s on s.id=r.shift_id where r.location_id=:l and r.date>=:a and r.date<=:b", l=location_id, a=str(mon), b=str(sun))}
        lv = many("select lv.employee_id, lv.from_date, lv.to_date from leave_request lv join employee e on e.id=lv.employee_id where e.location_id=:l and lv.status='approved' and lv.from_date<=:b and lv.to_date>=:a", l=location_id, a=str(mon), b=str(sun))
        lt = one("select type from location where id=:i", i=location_id)["type"]; mn = MIN_COVER.get(lt, 0); days = [mon + timedelta(days=i) for i in range(7)]
        rows, cov = [], {str(d): 0 for d in days}
        for s in staff:
            cs, hrs = [], 0.0
            for d in days:
                code = cells.get((s["id"], str(d))); onl = any(x["employee_id"] == s["id"] and x["from_date"] <= str(d) <= x["to_date"] for x in lv)
                if code and not onl: cov[str(d)] += 1
                if code: hrs += SHIFT_PAID[code]
                cs.append(dict(date=str(d), shift=code, leave=onl and bool(code), locked=d < TODAY))
            rows.append(dict(id=s["id"], name=s["name"], code=s["emp_code"], des=s["des"], status=s["status"], hours=hrs, days=cs))
        return dict(week=str(mon), location_id=location_id, min_cover=mn, cover=[dict(date=k, n=v, gap=bool(mn) and v < mn) for k, v in cov.items()], rows=rows, today=str(TODAY))

    @app.put("/api/hr/roster")
    def roster_set(b: RosterIn, u=Depends(allr)):
        e = emp_or_404(b.employee_id, u); d = parse(b.date)
        if b.shift is not None: roster_checks(e, d, b.shift)
        elif d < TODAY: raise HTTPException(400, "Past days are locked")
        warn = None
        with engine.begin() as c:
            old = c.execute(text("select s.code from roster r join shift s on s.id=r.shift_id where r.employee_id=:e and r.date=:d"), dict(e=e["id"], d=d)).scalar()
            c.execute(text("delete from roster where employee_id=:e and date=:d"), dict(e=e["id"], d=d))
            if b.shift:
                sid = c.execute(text("select id from shift where code=:c"), dict(c=b.shift)).scalar()
                c.execute(text("insert into roster(employee_id, date, shift_id, location_id) values (:e,:d,:s,:l)"), dict(e=e["id"], d=d, s=sid, l=e["location_id"]))
            audit(c, u, "hr.roster.set", "roster", f"{e['id']}:{d}", dict(shift=old), dict(shift=b.shift))
        mn = MIN_COVER.get(e["lt"], 0)
        if mn:
            n, _ = cover(e["location_id"], d)
            if n < mn: warn = f"{e['lname']} has {n} on shift on {d:%d %b}, below the minimum of {mn}"
        return dict(ok=True, warning=warn)

    @app.post("/api/hr/roster/copy")
    def roster_copy(b: CopyIn, u=Depends(allr)):
        loc = need_loc(u, b.location_id); mon = week_of(parse(b.week))
        if mon <= TODAY: raise HTTPException(400, "Pick a week that starts after today")
        prev = mon - timedelta(days=7)
        src = many("select r.employee_id, r.date, s.code, s.id sid from roster r join shift s on s.id=r.shift_id where r.location_id=:l and r.date>=:a and r.date<:b", l=b.location_id, a=str(prev), b=str(mon))
        have = {(r["employee_id"], r["date"]) for r in many("select employee_id, date from roster where location_id=:l and date>=:a and date<:b", l=b.location_id, a=str(mon), b=str(mon + timedelta(days=7)))}
        n = 0
        with engine.begin() as c:
            for r in src:
                d = parse(r["date"]) + timedelta(days=7)
                if (r["employee_id"], str(d)) in have: continue
                e = c.execute(text("select join_date, exit_date, status from employee where id=:i"), dict(i=r["employee_id"])).fetchone()
                if e.status == "exited" or (e.exit_date and d > parse(e.exit_date)) or parse(e.join_date) > d: continue
                if c.execute(text("select 1 from leave_request where employee_id=:e and status='approved' and from_date<=:d and to_date>=:d"), dict(e=r["employee_id"], d=d)).fetchone(): continue
                c.execute(text("insert into roster(employee_id, date, shift_id, location_id) values (:e,:d,:s,:l)"), dict(e=r["employee_id"], d=d, s=r["sid"], l=b.location_id)); n += 1
            audit(c, u, "hr.roster.copy", "roster", f"{b.location_id}:{mon}", None, dict(copied=n))
        return dict(copied=n)

    # ---------------- leave ----------------
    def leave_row(lid, u):
        r = one("select lr.*, t.code, t.name tname, t.annual_quota q from leave_request lr join leave_type t on t.id=lr.leave_type_id where lr.id=:i", i=lid)
        if not r: raise HTTPException(404, "Leave request not found")
        return r, emp_or_404(r["employee_id"], u)

    def cover_violations(e, f, t, skip=None):
        mn = MIN_COVER.get(e["lt"], 0); out = []
        if not mn: return out
        for r in many("select date from roster where employee_id=:e and date>=:a and date<=:b and date>=:t", e=e["id"], a=str(f), b=str(t), t=str(TODAY)):
            n, _ = cover(e["location_id"], parse(r["date"]), skip)
            if n - 1 < mn: out.append(dict(date=r["date"], after=n - 1, min=mn))
        return out

    @app.get("/api/hr/leave")
    def leave_list(status: str = "pending", q: str = "", location_id: int = 0, page: int = 1, size: int = 25, u=Depends(allr)):
        page, size = pager(page, size); sl = scope_loc(u); w, p = "", dict(n=size, o=(page - 1) * size, t=str(TODAY - timedelta(days=AGED_LEAVE_DAYS)))
        if sl: w += " and e.location_id=:sl"; p["sl"] = sl
        elif location_id: w += " and e.location_id=:sl"; p["sl"] = location_id
        if status in ("pending", "approved", "rejected", "cancelled"): w += " and lr.status=:st"; p["st"] = status
        if q: w += " and (lower(e.name) like :q or lower(e.emp_code) like :q)"; p["q"] = f"%{q.lower()}%"
        base = "from leave_request lr join employee e on e.id=lr.employee_id join leave_type t on t.id=lr.leave_type_id join location l on l.id=e.location_id join designation g on g.id=e.designation_id where 1=1" + w
        rows = many("select lr.id, lr.employee_id, e.name, e.emp_code, g.title des, l.name loc, l.type lt, t.code, lr.from_date, lr.to_date, lr.days, lr.status, lr.reason, lr.applied_on, lr.decided_on, lr.decision_note, (lr.applied_on<=:t) aged " + base +
                    " order by case lr.status when 'pending' then 0 else 1 end, case lr.status when 'pending' then lr.applied_on end, lr.from_date desc limit :n offset :o", **p)
        for r in rows:
            r["aged"] = bool(r["aged"]) and r["status"] == "pending"
            if r["status"] == "pending" and r["lt"] in MIN_COVER and r["to_date"] >= str(TODAY):
                r["risk"] = bool(cover_violations(dict(id=r["employee_id"], lt=r["lt"], location_id=one("select location_id from employee where id=:i", i=r["employee_id"])["location_id"]), parse(r["from_date"]), parse(r["to_date"])))
        return dict(total=one("select count(*) n " + base, **p)["n"], rows=rows)

    @app.post("/api/hr/leave")
    def leave_apply(b: LeaveIn, u=Depends(allr)):
        e = emp_or_404(b.employee_id, u); f, t = parse(b.from_date, "From date"), parse(b.to_date, "To date")
        tp = one("select * from leave_type where code=:c", c=b.type)
        if not tp: raise HTTPException(400, "Unknown leave type")
        if e["status"] not in ("active", "notice"): raise HTTPException(409, "Employee is not on the active roll")
        if t < f: raise HTTPException(400, "To date is before from date")
        if f < TODAY - timedelta(days=BACKDATE_DAYS): raise HTTPException(400, f"Cannot back-date leave by more than {BACKDATE_DAYS} days")
        if f.year != t.year: raise HTTPException(400, "Split leave that crosses the year end into two requests")
        if tp["code"] == "WFH" and e["lt"] != "office": raise HTTPException(400, "Work from home is for office staff")
        if e["exit_date"] and t > parse(e["exit_date"]): raise HTTPException(409, "Leave runs past the last working day")
        days = leave_days(e, f, t)
        if days <= 0: raise HTTPException(400, "No working days in that range")
        if one("select id from leave_request where employee_id=:e and status in ('pending','approved') and from_date<=:t and to_date>=:f", e=e["id"], f=str(f), t=str(t)): raise HTTPException(409, "Overlaps another leave request")
        bal = next(x for x in balances(e, f.year) if x["code"] == tp["code"])
        if days > bal["left"]: raise HTTPException(409, f"Only {bal['left']} days of {tp['name'].lower()} left this year")
        with engine.begin() as c:
            c.execute(text("insert into leave_request(employee_id, leave_type_id, from_date, to_date, status, is_wfh, approver_id, days, reason, applied_on) values (:e,:t,:f,:to,'pending',:w,:a,:d,:r,:ap)"),
                      dict(e=e["id"], t=tp["id"], f=f, to=t, w=tp["code"] == "WFH", a=e["manager_id"], d=days, r=(b.reason or "")[:200] or None, ap=TODAY))
            lid = c.execute(text("select max(id) from leave_request where employee_id=:e"), dict(e=e["id"])).scalar()
            audit(c, u, "hr.leave.apply", "leave_request", lid, None, dict(type=tp["code"], days=days, from_date=str(f), to_date=str(t)))
        return dict(id=lid, days=days)

    @app.post("/api/hr/leave/{lid}/decide")
    def leave_decide(lid: int, b: DecideIn, u=Depends(allr)):
        r, e = leave_row(lid, u); f, t = parse(r["from_date"]), parse(r["to_date"])
        if u["role"] in MGR and e["des"] in ("Store Manager", "Warehouse Manager"): raise HTTPException(403, "A manager's leave is decided by HR or the regional manager")
        if b.action in ("approve", "reject") and r["status"] != "pending": raise HTTPException(409, f"Already {r['status']}")
        note = (b.note or "").strip()[:200]
        with engine.begin() as c:
            if b.action == "approve":
                if r["days"] > LONG_LEAVE and not is_hr(u): raise HTTPException(403, f"Leave above {LONG_LEAVE} days needs HR")
                if t < TODAY - timedelta(days=BACKDATE_DAYS): raise HTTPException(409, "These dates are too old to approve")
                bal = next(x for x in balances(e, f.year) if x["code"] == r["code"])
                if r["days"] > bal["q"] - bal["used"]: raise HTTPException(409, f"Not enough {r['tname'].lower()} balance")
                if one("select id from leave_request where employee_id=:e and status='approved' and id!=:i and from_date<=:t and to_date>=:f", e=e["id"], i=lid, f=str(f), t=str(t)): raise HTTPException(409, "Overlaps approved leave")
                v = cover_violations(e, f, t, skip=lid)
                if v and not (b.force and is_hr(u)):
                    d0 = v[0]; raise HTTPException(409, f"Coverage: {e['lname']} would have {d0['after']} on shift on {parse(d0['date']):%d %b}, below the minimum of {d0['min']}." + (" HR can approve with an override." if not is_hr(u) else " Approve with override if you accept the gap."))
                if v and not note: note = "Approved with coverage override"
                c.execute(text("update leave_request set status='approved', decided_on=:d, decision_note=:n where id=:i"), dict(d=TODAY, n=note or None, i=lid))
            elif b.action == "reject":
                if len(note) < 3: raise HTTPException(400, "Give a reason for rejecting")
                c.execute(text("update leave_request set status='rejected', decided_on=:d, decision_note=:n where id=:i"), dict(d=TODAY, n=note, i=lid))
            elif b.action == "cancel":
                if r["status"] not in ("pending", "approved"): raise HTTPException(409, f"Already {r['status']}")
                if r["status"] == "approved" and f <= TODAY: raise HTTPException(409, "Leave has started. Correct the attendance instead")
                c.execute(text("update leave_request set status='cancelled', decided_on=:d, decision_note=:n where id=:i"), dict(d=TODAY, n=note or None, i=lid))
            else: raise HTTPException(400, "Action must be approve, reject or cancel")
            audit(c, u, "hr.leave." + b.action, "leave_request", lid, dict(status=r["status"]), dict(note=note, force=b.force))
        return one("select id, status, decided_on, decision_note from leave_request where id=:i", i=lid)

    # ---------------- celebrations ----------------
    @app.get("/api/hr/celebrations")
    def celebrations(days: int = 14, u=Depends(allr)):
        days = max(1, min(days, 60)); sl = scope_loc(u); end = TODAY + timedelta(days=days)
        rows = many("select e.id, e.name, g.title des, l.name loc, e.join_date, e.birth_date, e.status from employee e join designation g on g.id=e.designation_id join location l on l.id=e.location_id where e.status in ('active','notice','joining') and (:s is null or e.location_id=:s)", s=sl)

        def nxt(d):
            for y in (TODAY.year, TODAY.year + 1):
                try: x = date(y, d.month, d.day)
                except ValueError: x = date(y, 3, 1)
                if TODAY <= x <= end: return x
        b, a, j = [], [], []
        for r in rows:
            bd, jd = parse(r["birth_date"]), parse(r["join_date"])
            if r["status"] != "joining":
                x = nxt(bd)
                if x: b.append(dict(id=r["id"], name=r["name"], des=r["des"], loc=r["loc"], date=str(x)))
                y = nxt(jd)
                if y and y.year > jd.year: a.append(dict(id=r["id"], name=r["name"], des=r["des"], loc=r["loc"], date=str(y), years=y.year - jd.year))
            if TODAY <= jd <= end: j.append(dict(id=r["id"], name=r["name"], des=r["des"], loc=r["loc"], date=str(jd)))
        return dict(days=days, birthdays=sorted(b, key=lambda x: x["date"]), anniversaries=sorted(a, key=lambda x: x["date"]), joiners=sorted(j, key=lambda x: x["date"]))

    # ---------------- onboarding ----------------
    @app.get("/api/hr/onboarding")
    def onboarding(u=Depends(allr)):
        sl = scope_loc(u)
        emps = many("select e.id, e.name, e.emp_code, e.join_date, g.title des, l.name loc from employee e join designation g on g.id=e.designation_id join location l on l.id=e.location_id where e.join_date>=:a and e.join_date<=:b and e.status in ('active','joining','notice') and (:s is null or e.location_id=:s) order by e.join_date",
                    a=str(TODAY - timedelta(days=45)), b=str(TODAY + timedelta(days=60)), s=sl)
        tasks = many("select t.id, t.employee_id, t.task, t.due_date, t.done_at from onboarding_task t join employee e on e.id=t.employee_id where e.join_date>=:a and e.join_date<=:b and (:s is null or e.location_id=:s) order by t.due_date, t.id", a=str(TODAY - timedelta(days=45)), b=str(TODAY + timedelta(days=60)), s=sl)
        by = {}
        for t in tasks: by.setdefault(t["employee_id"], []).append(dict(t, overdue=t["done_at"] is None and t["due_date"] < str(TODAY)))
        out = []
        for e in emps:
            ts = by.get(e["id"], [])
            out.append(dict(e, joined=e["join_date"] <= str(TODAY), done=sum(1 for t in ts if t["done_at"]), total=len(ts), overdue=sum(1 for t in ts if t["overdue"]), tasks=ts))
        return dict(rows=out, overdue=sum(x["overdue"] for x in out))

    @app.post("/api/hr/onboarding/tasks/{tid}/done")
    def onboarding_done(tid: int, b: DoneIn, u=Depends(allr)):
        t = one("select * from onboarding_task where id=:i", i=tid)
        if not t: raise HTTPException(404, "Task not found")
        emp_or_404(t["employee_id"], u)
        with engine.begin() as c:
            c.execute(text("update onboarding_task set done_at=:d where id=:i"), dict(d=NOW if b.done else None, i=tid))
            audit(c, u, "hr.onboarding." + ("done" if b.done else "undo"), "onboarding_task", tid, dict(done_at=str(t["done_at"])), dict(done=b.done))
        return dict(id=tid, done=b.done)

    # ---------------- recruitment ----------------
    def job_or_404(jid):
        j = one("select * from job_posting where id=:i", i=jid)
        if not j: raise HTTPException(404, "Job posting not found")
        return j

    @app.get("/api/hr/jobs")
    def jobs(status: str = "open", u=Depends(hrr)):
        rows = many("select j.id, j.title, j.status, j.openings, j.posted_on, j.closes_on, d.name dept, l.name loc, l.city, "
                    "(select count(*) from applicant a where a.job_id=j.id) apps, (select count(*) from applicant a where a.job_id=j.id and a.stage='Hired') hired, "
                    "(select count(*) from applicant a where a.job_id=j.id and a.stage in ('Applied','Screen','Interview','Offer')) active from job_posting j join department d on d.id=j.department_id left join location l on l.id=j.location_id "
                    "where (:s='' or j.status=:s) order by j.status, j.posted_on desc", s=status if status in ("open", "closed") else "")
        for r in rows: r["age"] = (TODAY - parse(r["posted_on"])).days; r["thin"] = r["status"] == "open" and r["active"] < 3 * max(r["openings"] - r["hired"], 1)
        return dict(rows=rows)

    @app.get("/api/hr/jobs/{jid}")
    def job(jid: int, u=Depends(hrr)):
        j = job_or_404(jid)
        return dict(job=j, applicants=many("select id, name, email, stage, applied_on, source, stage_changed_on, employee_id from applicant where job_id=:i order by case stage when 'Offer' then 0 when 'Interview' then 1 when 'Screen' then 2 when 'Applied' then 3 else 4 end, applied_on", i=jid), next=NEXT)

    @app.post("/api/hr/jobs")
    def job_new(b: JobIn, u=Depends(hrr)):
        if len(b.title.strip()) < 3: raise HTTPException(400, "Give a job title")
        if not 1 <= b.openings <= 20: raise HTTPException(400, "Openings must be between 1 and 20")
        if not one("select id from department where id=:i", i=b.department_id) or not one("select id from designation where id=:i", i=b.designation_id): raise HTTPException(400, "Unknown department or designation")
        if b.location_id and not one("select id from location where id=:i", i=b.location_id): raise HTTPException(400, "Unknown location")
        co = parse(b.closes_on) if b.closes_on else TODAY + timedelta(days=45)
        if co <= TODAY: raise HTTPException(400, "Closing date must be in the future")
        with engine.begin() as c:
            c.execute(text("insert into job_posting(title, department_id, location_id, status, posted_on, closes_on, description, designation_id, openings) values (:t,:d,:l,'open',:p,:c,:ds,:g,:o)"),
                      dict(t=b.title.strip()[:120], d=b.department_id, l=b.location_id, p=TODAY, c=co, ds=(b.description or "")[:2000], g=b.designation_id, o=b.openings))
            jid = c.execute(text("select max(id) from job_posting")).scalar()
            audit(c, u, "hr.job.create", "job_posting", jid, None, dict(title=b.title, openings=b.openings))
        return dict(id=jid)

    @app.post("/api/hr/jobs/{jid}/close")
    def job_close(jid: int, u=Depends(hrr)):
        j = job_or_404(jid)
        if j["status"] != "open": raise HTTPException(409, "Already closed")
        with engine.begin() as c:
            c.execute(text("update job_posting set status='closed' where id=:i"), dict(i=jid))
            c.execute(text("update applicant set stage='Rejected', stage_changed_on=:d where job_id=:i and stage in ('Applied','Screen','Interview','Offer')"), dict(i=jid, d=TODAY))
            audit(c, u, "hr.job.close", "job_posting", jid, dict(status="open"), dict(status="closed"))
        return dict(id=jid, status="closed")

    @app.post("/api/hr/applicants")
    def applicant_new(b: AppIn, u=Depends(hrr)):
        j = job_or_404(b.job_id)
        if j["status"] != "open": raise HTTPException(409, "This posting is closed")
        if len(b.name.strip()) < 2 or not MAIL.match(b.email.strip()): raise HTTPException(400, "Give a name and a valid email")
        if one("select id from applicant where job_id=:j and lower(email)=:e", j=b.job_id, e=b.email.strip().lower()): raise HTTPException(409, "This email has already applied for the job")
        with engine.begin() as c:
            c.execute(text("insert into applicant(job_id, name, stage, applied_on, source, email, stage_changed_on) values (:j,:n,'Applied',:d,:s,:e,:d)"), dict(j=b.job_id, n=b.name.strip()[:80], d=TODAY, s=b.source[:20], e=b.email.strip().lower()))
            aid = c.execute(text("select max(id) from applicant")).scalar(); audit(c, u, "hr.applicant.create", "applicant", aid, None, dict(job_id=b.job_id))
        return dict(id=aid)

    @app.post("/api/hr/applicants/{aid}/stage")
    def applicant_stage(aid: int, b: StageIn, u=Depends(hrr)):
        a = one("select * from applicant where id=:i", i=aid)
        if not a: raise HTTPException(404, "Applicant not found")
        if b.stage not in NEXT[a["stage"]]: raise HTTPException(409, f"{a['stage']} cannot move to {b.stage}. Allowed: {', '.join(NEXT[a['stage']]) or 'none'}")
        j = job_or_404(a["job_id"]); emp_id = None
        if j["status"] != "open": raise HTTPException(409, "This posting is closed")
        with engine.begin() as c:
            if b.stage == "Hired":
                hired = c.execute(text("select count(*) from applicant where job_id=:j and stage='Hired'"), dict(j=j["id"])).scalar()
                if hired >= j["openings"]: raise HTTPException(409, "All openings are already filled")
                if not b.birth_date: raise HTTPException(400, "Date of birth is needed to create the employee")
                bd = parse(b.birth_date, "Date of birth"); age = (TODAY - bd).days / 365.25
                if not 18 <= age <= 70: raise HTTPException(400, "Employee must be between 18 and 70")
                jd = parse(b.join_date, "Join date") if b.join_date else TODAY + timedelta(days=14)
                if not TODAY <= jd <= TODAY + timedelta(days=90): raise HTTPException(400, "Join date must be within the next 90 days")
                loc = j["location_id"] or c.execute(text("select id from location where type='office' order by id limit 1")).scalar()
                ltype = c.execute(text("select type from location where id=:i"), dict(i=loc)).scalar()
                mt = "Store Manager" if ltype == "store" else "Warehouse Manager" if ltype == "warehouse" else "Head of Department"
                mgr = c.execute(text("select e.id from employee e join designation g on g.id=e.designation_id where g.title=:t and e.status in ('active','notice') and (e.location_id=:l or :o=1) and e.department_id=:d order by e.id limit 1"),
                                dict(t=mt, l=loc, o=0 if ltype != "office" else 1, d=j["department_id"])).scalar() or c.execute(text("select id from employee where manager_id is null order by id limit 1")).scalar()
                nid = c.execute(text("select coalesce(max(id),0)+1 from employee")).scalar()
                c.execute(text("insert into employee(emp_code, name, department_id, designation_id, location_id, manager_id, join_date, birth_date, status) values (:c,:n,:d,:g,:l,:m,:j,:b,'joining')"),
                          dict(c=f"E{nid:05d}", n=a["name"], d=j["department_id"], g=j["designation_id"], l=loc, m=mgr, j=jd, b=bd))
                emp_id = c.execute(text("select id from employee where emp_code=:c"), dict(c=f"E{nid:05d}")).scalar()
                for t, off in TASKS: c.execute(text("insert into onboarding_task(employee_id, task, due_date) values (:e,:t,:d)"), dict(e=emp_id, t=t, d=jd + timedelta(days=off)))
                if hired + 1 >= j["openings"]:
                    c.execute(text("update job_posting set status='closed' where id=:i"), dict(i=j["id"]))
                    c.execute(text("update applicant set stage='Rejected', stage_changed_on=:d where job_id=:j and id!=:a and stage in ('Applied','Screen','Interview','Offer')"), dict(d=TODAY, j=j["id"], a=aid))
            c.execute(text("update applicant set stage=:s, stage_changed_on=:d, employee_id=:e where id=:i"), dict(s=b.stage, d=TODAY, e=emp_id, i=aid))
            audit(c, u, "hr.applicant.stage", "applicant", aid, dict(stage=a["stage"]), dict(stage=b.stage, employee_id=emp_id))
        return dict(id=aid, stage=b.stage, employee_id=emp_id)

    # ---------------- public careers feed (no sign in, no applicant data) ----------------
    def open_jobs():
        return many("select j.id, j.title, d.name dept, coalesce(l.city, 'Bengaluru') city, j.closes_on, j.description, j.openings - (select count(*) from applicant a where a.job_id=j.id and a.stage='Hired') slots from job_posting j join department d on d.id=j.department_id left join location l on l.id=j.location_id "
                    "where j.status='open' and (j.closes_on is null or j.closes_on>=:t) order by j.posted_on desc", t=str(TODAY))

    @app.get("/api/public/careers")
    def careers(): return [r for r in open_jobs() if r["slots"] > 0]

    @app.post("/api/public/careers/{jid}/apply")
    def careers_apply(jid: int, b: ApplyIn):
        if jid not in {r["id"] for r in open_jobs() if r["slots"] > 0}: raise HTTPException(404, "This job is not open")
        if len(b.name.strip()) < 2 or len(b.name) > 80 or not MAIL.match(b.email.strip()): raise HTTPException(400, "Give your name and a valid email")
        if one("select id from applicant where job_id=:j and lower(email)=:e", j=jid, e=b.email.strip().lower()): raise HTTPException(409, "You have already applied for this job")
        with engine.begin() as c:
            c.execute(text("insert into applicant(job_id, name, stage, applied_on, source, email, stage_changed_on) values (:j,:n,'Applied',:d,'Careers page',:e,:d)"), dict(j=jid, n=b.name.strip(), d=TODAY, e=b.email.strip().lower()))
        return dict(ok=True)

    # ---------------- Control Tower hooks ----------------
    def exceptions(f):
        out, sc = [], f["store_ids"]
        sl = "" if sc is None else " and e.location_id in (" + ",".join(str(int(x)) for x in sc) + ")"
        al = "" if sc is None else " and location_id in (" + ",".join(str(int(x)) for x in sc) + ")"
        gl = "" if sc is None else " and r.location_id in (" + ",".join(str(int(x)) for x in sc) + ")"
        g = many("select l.name, l.city, r.date, count(*) n from roster r join location l on l.id=r.location_id where l.type='store' and r.date>=:a and r.date<=:b" + gl +
                 " and r.employee_id not in (select lv.employee_id from leave_request lv where lv.status='approved' and lv.from_date<=r.date and lv.to_date>=r.date) group by r.location_id, r.date having count(*)<%d order by r.date" % MIN_COVER["store"], a=str(TODAY), b=str(TODAY + timedelta(days=6)))
        if g:
            names = sorted({x["name"] for x in g})
            out.append(dict(type="hr_cover", severity="high", title=f"{len(names)} stores will have fewer than {MIN_COVER['store']} people on shift this week", detail=f"First gap {parse(g[0]['date']):%a %d %b} at {g[0]['name']}, {g[0]['city']}. Fix the roster or move someone in.", ref="roster"))
        lv = one("select count(*) n from leave_request lr join employee e on e.id=lr.employee_id where lr.status='pending' and lr.applied_on<=:t" + sl, t=str(TODAY - timedelta(days=AGED_LEAVE_DAYS)))["n"]
        if lv: out.append(dict(type="hr_leave", severity="med", title=f"{lv} leave requests have waited more than {AGED_LEAVE_DAYS} days", detail="Approve or reject so staff can plan and rosters stay accurate.", ref="leave"))
        mp = one("select count(*) n from attendance where status='M' and date>=:a and date<:b" + al, a=str(TODAY - timedelta(days=30)), b=str(TODAY - timedelta(days=7)))["n"]
        if mp: out.append(dict(type="hr_punch", severity="med", title=f"{mp} missing punch-outs are older than 7 days", detail="Store managers can no longer fix these. HR can correct them for 30 days.", ref="attendance"))
        if sc is None:
            for w in many("select l.name, count(*) n from employee e join location l on l.id=e.location_id where l.type='warehouse' and e.status='exited' group by l.id having count(*)>=4 order by n desc"):
                out.append(dict(type="hr_attrition", severity="med", title=f"{w['name']} lost {w['n']} people in 90 days", detail="Check absence, hiring pipeline and shift timings. Open postings are in People.", ref="headcount"))
        return out

    return dict(exceptions=exceptions)
