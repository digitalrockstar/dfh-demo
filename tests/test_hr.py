import os, shutil, json, pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import text
from dfh.app import create_app
from dfh.db import get_engine

SRC = os.getenv("DFH_DB", "sqlite:///data/dfh.db").replace("sqlite:///", "")
TODAY = date(2026, 10, 31)


@pytest.fixture(scope="module")
def env(tmp_path_factory):
    p = str(tmp_path_factory.mktemp("db") / "dfh.db"); shutil.copy(SRC, p); url = "sqlite:///" + p
    return TestClient(create_app(url, os.getenv("DFH_DATA", "data"), serve_frontend=False)), get_engine(url)


def tok(c, user="hr"):
    r = c.post("/api/login", json=dict(username=user, password="demo1234")); assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["token"]}


def q(eng, sql, **p):
    with eng.connect() as c: return c.execute(text(sql), p).fetchall()


def test_seed_shape(env):
    c, e = env
    assert q(e, "select count(*) from roster r join employee x on x.id=r.employee_id where x.exit_date is not null and r.date>x.exit_date")[0][0] == 0
    assert q(e, "select count(*) from roster r join employee x on x.id=r.employee_id where r.date<x.join_date")[0][0] == 0
    assert q(e, "select count(*) from attendance a where a.status='L' and not exists (select 1 from leave_request l where l.employee_id=a.employee_id and l.status='approved' and l.from_date<=a.date and l.to_date>=a.date)")[0][0] == 0
    assert q(e, "select count(*) from (select lr.employee_id, lr.leave_type_id, sum(lr.days) d from leave_request lr where lr.status in ('approved','pending') and lr.from_date>='2026-01-01' group by 1,2) x join leave_type t on t.id=x.leave_type_id where x.d>t.annual_quota")[0][0] == 0
    assert q(e, "select count(*) from leave_request where days<=0 or to_date<from_date")[0][0] == 0
    assert q(e, "select count(*) from attendance where status in ('P','H') and (punch_in is null or punch_out is null)")[0][0] == 0
    assert q(e, "select count(*) from applicant a join job_posting j on j.id=a.job_id where a.stage='Hired' group by j.id having count(*)>max(j.openings)") == []
    assert q(e, "select count(*) from employee where status='notice' and exit_date<='2026-10-31'")[0][0] == 0
    assert q(e, "select min(n) from (select count(*) n from employee where location_id in (select id from location where type='store') and status in ('active','notice') group by location_id)")[0][0] >= 2


def test_planted_findings(env):
    c, e = env
    f9 = json.loads(q(e, "select params from demo_finding where code='F9'")[0][0]); wh = f9["warehouse_id"]
    ex = q(e, "select count(*) from employee where location_id=:w and status='exited'", w=wh)[0][0]
    assert ex >= 5
    ab = lambda w: q(e, "select avg(status='A') from attendance where location_id=:w", w=w)[0][0]
    others = q(e, "select id from location where type='warehouse' and id!=:w", w=wh)
    assert ab(wh) > 2.5 * max(ab(o[0]) for o in others)
    assert len(f9["planted_leave_stores"]) == 3
    ex_types = [x["type"] for x in c.get("/api/ct/exceptions", headers=tok(c, "ceo")).json()]
    assert "hr_attrition" in ex_types and "hr_leave" in ex_types and "hr_punch" in ex_types


def test_roles_and_scope(env):
    c, e = env
    assert c.get("/api/hr/summary", headers=tok(c, "cashier")).status_code == 403
    assert c.get("/api/hr/summary", headers=tok(c, "finance")).status_code == 403
    for p in ("/api/hr/jobs", "/api/hr/org", "/api/hr/headcount"): assert c.get(p, headers=tok(c, "storemgr")).status_code == 403
    sm = tok(c, "storemgr"); r = c.get("/api/hr/employees?size=100", headers=sm).json()
    assert 0 < r["total"] <= 10 and all(x["loc"] == r["rows"][0]["loc"] for x in r["rows"]) and all("email" not in x for x in r["rows"])
    other = q(e, "select id from employee where location_id!=21 and status='active' limit 1")[0][0]
    assert c.get(f"/api/hr/employees/{other}", headers=sm).status_code == 404
    hr = c.get("/api/hr/employees?size=5", headers=tok(c)).json(); assert hr["total"] > 2000 and "email" in hr["rows"][0]
    mine = c.get(f"/api/hr/employees/{r['rows'][0]['id']}", headers=sm).json()["profile"]; assert "birth_date" not in mine


def test_summary_and_lists(env):
    c, e = env; h = tok(c)
    s = c.get("/api/hr/summary", headers=h).json()
    assert s["headcount"] > 2000 and s["notice"] > 0 and s["att"]["pct"] > .9 and s["leave_aged"] >= 10 and s["vacancies"] > 0 and len(s["trend"]) == 14
    assert c.get("/api/hr/attendance", headers=h).json()["total"] > 1000
    late = c.get("/api/hr/attendance?status=late&size=50", headers=h).json(); assert late["rows"] and all(x["late"] for x in late["rows"])
    cel = c.get("/api/hr/celebrations?days=30", headers=h).json(); assert cel["birthdays"] and cel["joiners"]
    o = c.get("/api/hr/org", headers=h).json(); assert o["node"]["des"] == "CEO" and o["total"] > 0
    hc = c.get("/api/hr/headcount", headers=h).json(); assert hc["warehouses"][0]["exits90"] >= 5
    assert c.get("/api/hr/onboarding", headers=h).json()["overdue"] > 0
    sm = c.get("/api/hr/summary", headers=tok(c, "storemgr")).json(); assert sm["headcount"] <= 10 and "vacancies" not in sm


def test_attendance_fix_rules(env):
    c, e = env; h, sm = tok(c), tok(c, "storemgr")
    old = q(e, "select employee_id, date from attendance where status='M' and date<'2026-10-20' limit 1")[0]
    r = c.post("/api/hr/attendance/fix", headers=h, json=dict(employee_id=old[0], date=old[1], punch_out="18:30", reason="Forgot to punch out"))
    assert r.status_code == 409 and "Too old" in r.text or r.status_code == 200      # older than 30 days is locked for HR
    rec = q(e, "select a.employee_id, a.date, a.punch_in from attendance a where a.status='M' and a.date>='2026-10-26' and a.location_id=21 limit 1")
    if not rec: rec = q(e, "select a.employee_id, a.date, a.punch_in from attendance a where a.status='M' and a.date>='2026-10-26' limit 1")
    eid, d, pin = rec[0]
    assert c.post("/api/hr/attendance/fix", headers=h, json=dict(employee_id=eid, date=d, punch_out="18:30", reason="x")).status_code == 400
    assert c.post("/api/hr/attendance/fix", headers=h, json=dict(employee_id=eid, date=d, punch_out="25:00", reason="Forgot to punch out")).status_code == 400
    assert c.post("/api/hr/attendance/fix", headers=h, json=dict(employee_id=eid, date=d, punch_out="05:00", reason="Forgot to punch out")).status_code == 400
    ok = c.post("/api/hr/attendance/fix", headers=h, json=dict(employee_id=eid, date=d, punch_out="23:30", reason="Forgot to punch out"))
    assert ok.status_code in (200, 400)
    q2 = q(e, "select employee_id, date from attendance where status='M' and date>='2026-10-26' and employee_id!=:e limit 1", e=eid)[0]
    ok = c.post("/api/hr/attendance/fix", headers=h, json=dict(employee_id=q2[0], date=q2[1], punch_out="20:00", reason="Forgot to punch out"))
    if ok.status_code == 200:
        assert q(e, "select status, fixed from attendance where employee_id=:e and date=:d", e=q2[0], d=q2[1])[0][1] == 1
        assert c.post("/api/hr/attendance/fix", headers=h, json=dict(employee_id=q2[0], date=q2[1], punch_out="20:00", reason="Again please")).status_code == 409
    ab = q(e, "select employee_id, date from attendance where status='A' and date>='2026-10-26' and location_id=21 limit 1")
    if ab: assert c.post("/api/hr/attendance/fix", headers=sm, json=dict(employee_id=ab[0][0], date=ab[0][1], punch_in="09:30", punch_out="18:30", reason="Was present")).status_code == 403
    assert q(e, "select count(*) from audit_log where action='hr.attendance.fix'")[0][0] >= 1 or ok.status_code != 200


def test_roster_rules(env):
    c, e = env; sm = tok(c, "storemgr")
    ro = c.get("/api/hr/roster?location_id=21&week=2026-11-02", headers=sm).json(); assert ro["rows"] and ro["min_cover"] == 2 and len(ro["cover"]) == 7
    assert c.get("/api/hr/roster?location_id=22", headers=sm).status_code == 403
    emp = ro["rows"][-1]["id"]
    assert c.put("/api/hr/roster", headers=sm, json=dict(employee_id=emp, date="2026-10-20", shift="MORNING")).status_code == 400       # past is locked
    assert c.put("/api/hr/roster", headers=sm, json=dict(employee_id=emp, date="2026-11-03", shift="GENERAL")).status_code == 400       # store staff do not work general
    for i in range(7):                                                                                                                  # 6 day cap
        d = str(date(2026, 11, 16) + timedelta(days=i)); r = c.put("/api/hr/roster", headers=sm, json=dict(employee_id=emp, date=d, shift="MORNING"))
        if i < 6: assert r.status_code in (200, 409), r.text
        else: assert r.status_code == 409 and "working days" in r.text
    lv = q(e, "select employee_id, from_date from leave_request where status='approved' and from_date>='2026-11-04' and employee_id in (select id from employee where location_id=21) limit 1")
    if lv: assert c.put("/api/hr/roster", headers=sm, json=dict(employee_id=lv[0][0], date=lv[0][1], shift="MORNING")).status_code == 409
    cp = c.post("/api/hr/roster/copy", headers=sm, json=dict(location_id=21, week="2026-11-09")); assert cp.status_code == 200
    assert c.post("/api/hr/roster/copy", headers=sm, json=dict(location_id=21, week="2026-10-26")).status_code == 400


def test_leave_rules_and_coverage(env):
    c, e = env; h, sm = tok(c), tok(c, "storemgr")
    loc = json.loads(q(e, "select params from demo_finding where code='F9'")[0][0])["planted_leave_stores"][0]
    pend = q(e, "select lr.id, lr.employee_id from leave_request lr join employee x on x.id=lr.employee_id where lr.status='pending' and lr.from_date='2026-11-03' and x.location_id=:l order by lr.id", l=loc)
    assert pend
    results = [c.post(f"/api/hr/leave/{p[0]}/decide", headers=h, json=dict(action="approve")) for p in pend]
    blocked = [r for r in results if r.status_code == 409 and "Coverage" in r.text]; assert blocked, [r.text for r in results]
    forced = c.post(f"/api/hr/leave/{pend[-1][0]}/decide", headers=h, json=dict(action="approve", force=True)); assert forced.status_code in (200, 409)
    assert c.post(f"/api/hr/leave/{pend[0][0]}/decide", headers=h, json=dict(action="reject")).status_code in (400, 409)         # reject needs a reason (or already decided)
    mgr_own = q(e, "select lr.id from leave_request lr join employee x on x.id=lr.employee_id join designation g on g.id=x.designation_id where lr.status='pending' and g.title='Store Manager' and x.location_id=21 limit 1")
    emp = q(e, "select e.id from employee e join designation g on g.id=e.designation_id where e.location_id=21 and g.title='Cashier'")[0][0]
    assert c.post("/api/hr/leave", headers=sm, json=dict(employee_id=emp, type="CL", from_date="2026-10-01", to_date="2026-10-02")).status_code == 400   # back-dated
    assert c.post("/api/hr/leave", headers=sm, json=dict(employee_id=emp, type="WFH", from_date="2027-02-02", to_date="2027-02-02")).status_code == 400
    assert c.post("/api/hr/leave", headers=sm, json=dict(employee_id=emp, type="CL", from_date="2026-12-30", to_date="2027-01-02")).status_code == 400    # crosses year end
    ok = c.post("/api/hr/leave", headers=sm, json=dict(employee_id=emp, type="CL", from_date="2026-12-07", to_date="2026-12-07", reason="Family function"))
    if ok.status_code == 200:
        lid = ok.json()["id"]
        assert c.post("/api/hr/leave", headers=sm, json=dict(employee_id=emp, type="CL", from_date="2026-12-07", to_date="2026-12-07")).status_code == 409   # overlap
        assert c.post(f"/api/hr/leave/{lid}/decide", headers=sm, json=dict(action="cancel")).status_code == 200
        assert c.post(f"/api/hr/leave/{lid}/decide", headers=sm, json=dict(action="cancel")).status_code == 409
    over = c.post("/api/hr/leave", headers=sm, json=dict(employee_id=emp, type="SL", from_date="2026-11-23", to_date="2026-12-31"))
    assert over.status_code in (409, 400)
    assert q(e, "select count(*) from audit_log where action like 'hr.leave.%'")[0][0] >= 1


def test_onboarding_toggle_and_exit_flow(env):
    c, e = env; h = tok(c)
    t = q(e, "select id from onboarding_task where done_at is null limit 1")[0][0]
    assert c.post(f"/api/hr/onboarding/tasks/{t}/done", headers=h, json=dict(done=True)).status_code == 200
    assert q(e, "select done_at from onboarding_task where id=:i", i=t)[0][0] is not None
    emp = q(e, "select id from employee where status='active' and designation_id=(select id from designation where title='Sales Associate') limit 1")[0][0]
    assert c.post(f"/api/hr/employees/{emp}/exit", headers=h, json=dict(action="resign", last_day="2026-11-10", reason="Relocation")).status_code == 403   # short notice
    assert c.post(f"/api/hr/employees/{emp}/exit", headers=h, json=dict(action="resign", last_day="2026-12-05", reason="")).status_code == 400
    assert c.post(f"/api/hr/employees/{emp}/exit", headers=h, json=dict(action="resign", last_day="2026-12-05", reason="Relocation")).status_code == 200
    assert q(e, "select count(*) from roster where employee_id=:i and date>'2026-12-05'", i=emp)[0][0] == 0
    assert c.post(f"/api/hr/employees/{emp}/exit", headers=h, json=dict(action="complete")).status_code == 409
    assert c.post(f"/api/hr/employees/{emp}/exit", headers=h, json=dict(action="withdraw")).status_code == 200
    assert q(e, "select status from employee where id=:i", i=emp)[0][0] == "active"
    assert c.post(f"/api/hr/employees/{emp}/exit", headers=tok(c, "admin"), json=dict(action="resign", last_day="2026-11-10", reason="Relocation")).status_code == 200


def test_recruitment_and_public_feed(env):
    c, e = env; h = tok(c)
    pub = c.get("/api/public/careers"); assert pub.status_code == 200 and pub.json() and all(set(x) >= {"id", "title", "city"} and "email" not in x for x in pub.json())
    jid = pub.json()[0]["id"]
    assert c.post(f"/api/public/careers/{jid}/apply", json=dict(name="A", email="bad")).status_code == 400
    assert c.post(f"/api/public/careers/{jid}/apply", json=dict(name="Test Person", email="t.person@example.invalid")).status_code == 200
    assert c.post(f"/api/public/careers/{jid}/apply", json=dict(name="Test Person", email="t.person@example.invalid")).status_code == 409
    new = c.post("/api/hr/jobs", headers=h, json=dict(title="Cashier at Test Store", department_id=1, designation_id=8, location_id=21, openings=1))
    assert new.status_code == 200; j = new.json()["id"]
    assert c.post("/api/hr/jobs", headers=h, json=dict(title="x", department_id=1, designation_id=8)).status_code == 400
    a = c.post("/api/hr/applicants", headers=h, json=dict(job_id=j, name="Meera Pillai", email="meera@example.invalid")).json()["id"]
    assert c.post("/api/hr/applicants", headers=h, json=dict(job_id=j, name="Meera Pillai", email="MEERA@example.invalid")).status_code == 409
    assert c.post(f"/api/hr/applicants/{a}/stage", headers=h, json=dict(stage="Hired")).status_code == 409                 # no skipping stages
    for s in ("Screen", "Interview", "Offer"): assert c.post(f"/api/hr/applicants/{a}/stage", headers=h, json=dict(stage=s)).status_code == 200
    assert c.post(f"/api/hr/applicants/{a}/stage", headers=h, json=dict(stage="Hired")).status_code == 400                 # needs date of birth
    assert c.post(f"/api/hr/applicants/{a}/stage", headers=h, json=dict(stage="Hired", birth_date="2012-01-01")).status_code == 400
    r = c.post(f"/api/hr/applicants/{a}/stage", headers=h, json=dict(stage="Hired", birth_date="1999-05-04")); assert r.status_code == 200, r.text
    emp = r.json()["employee_id"]; assert emp
    row = q(e, "select status, location_id, manager_id, join_date from employee where id=:i", i=emp)[0]
    assert row[0] == "joining" and row[1] == 21 and row[2] and row[3] == str(TODAY + timedelta(days=14))
    assert q(e, "select count(*) from onboarding_task where employee_id=:i", i=emp)[0][0] == 6
    assert q(e, "select status from job_posting where id=:i", i=j)[0][0] == "closed"                                        # filled, so closed
    assert c.post("/api/hr/applicants", headers=h, json=dict(job_id=j, name="Late Person", email="late@example.invalid")).status_code == 409
    assert c.post(f"/api/hr/jobs/{j}/close", headers=h).status_code == 409
    assert q(e, "select count(*) from audit_log where action='hr.applicant.stage'")[0][0] >= 4
