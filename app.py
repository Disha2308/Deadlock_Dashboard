"""app.py - Streamlit dashboard. It only calls functions from algorithms.py / test_cases.py."""
import copy
import pandas as pd
import streamlit as st
import algorithms as alg
import test_cases as tc

st.set_page_config(page_title="Deadlock Analysis and Resource Allocation Dashboard",
                   page_icon="🔒", layout="wide")

st.markdown("""
<style>
.stApp {background: linear-gradient(160deg,#0b1020 0%,#10173a 100%);}
.hero h1 {background: linear-gradient(90deg,#a78bfa,#22d3ee); -webkit-background-clip:text;
          -webkit-text-fill-color:transparent; font-size:2.2rem; margin-bottom:0;}
.hero p {color:#b6bdd9; margin-top:.2rem;}
.card {background:#141b34; border:1px solid #2a3560; border-radius:14px; padding:14px 18px;}
.card .lbl {color:#22d3ee; font-size:.78rem; text-transform:uppercase; letter-spacing:.07em;}
.card .big {color:#e6e9f5; font-size:1.8rem; font-weight:700;}
.badge {display:inline-block; padding:6px 14px; border-radius:999px; font-weight:700;}
.ok {background:rgba(34,197,94,.15); color:#4ade80; border:1px solid #22c55e;}
.warn {background:rgba(251,191,36,.12); color:#fbbf24; border:1px solid #f59e0b;}
.bad {background:rgba(248,113,113,.13); color:#f87171; border:1px solid #ef4444;}
.seq {font-size:1.25rem; color:#22d3ee; font-weight:600; margin:.4rem 0;}
</style>""", unsafe_allow_html=True)

PAGES = ["Dashboard", "Check Safe State", "Request Resources", "Deadlock Lab"]
STATUS_CLASS = {alg.SAFE: "ok", alg.GRANTED: "ok", alg.NO_DEADLOCK: "ok", alg.ALLOWED: "ok",
                alg.UNSAFE: "warn", alg.DENIED_NEED: "warn", alg.DENIED_AVAILABLE: "warn",
                alg.DENIED_UNSAFE: "warn", alg.DEADLOCK: "bad", alg.INVALID: "bad",
                alg.REJECTED: "bad"}
ICON = {"ok": "✔", "warn": "⚠", "bad": "✖"}


def badge(status):
    cls = STATUS_CLASS.get(status, "warn")
    return f'<span class="badge {cls}">{ICON[cls]} {status}</span>'


def card(label, value):
    st.markdown(f'<div class="card"><div class="lbl">{label}</div><div class="big">{value}</div></div>',
                unsafe_allow_html=True)


def show_table(title, matrix, rows, cols):
    st.markdown(f"**{title}**")
    st.dataframe(pd.DataFrame(matrix, index=rows, columns=cols))


# ------------------------------------------------------------------ session state
def load_state(available, allocation, maximum):
    ss = st.session_state
    ss.available = list(available)
    ss.allocation = [list(r) for r in allocation]
    ss.maximum = [list(r) for r in maximum]
    ss.ver = ss.get("ver", 0) + 1
    ss.last_request = None


def load_det(data):
    ss = st.session_state
    ss.det = copy.deepcopy(data)
    ss.det_ver = ss.get("det_ver", 0) + 1


if "available" not in st.session_state:
    st.session_state.page = PAGES[0]
    load_state(tc.TC1_DATA["available"], tc.TC1_DATA["allocation"], tc.TC1_DATA["maximum"])
    load_det(tc.TC4_DATA)
ss = st.session_state


def go(page):
    st.session_state.page = page


def cb_load(data):
    load_state(data["available"], data["allocation"], data["maximum"])


def cb_load_det():
    load_det(tc.TC4_DATA)


def df_to_matrix(df):
    out = []
    for row in df.values.tolist():
        clean = []
        for v in row:
            if v is None or (isinstance(v, float) and v != v):
                clean.append(None)
            elif isinstance(v, float) and v.is_integer():
                clean.append(int(v))
            else:
                clean.append(v)
        out.append(clean)
    return out


def resize_state(n, m):
    old_n, old_m = len(ss.allocation), len(ss.available)
    if (n, m) == (old_n, old_m):
        return False

    def fit(row, length):
        row = list(row)[:length]
        return row + [0] * (length - len(row))

    ss.available = fit(ss.available, m)
    ss.allocation = [fit(ss.allocation[i], m) if i < old_n else [0] * m for i in range(n)]
    ss.maximum = [fit(ss.maximum[i], m) if i < old_n else [0] * m for i in range(n)]
    ss.ver += 1
    return True


def current_status():
    return alg.check_safe_state(ss.available, ss.allocation, ss.maximum)


# ------------------------------------------------------------------ renderers
def render_safety(res):
    st.markdown(badge(res["status"]), unsafe_allow_html=True)
    if res["status"] == alg.INVALID:
        for e in res["errors"]:
            st.error(e)
        return
    if res["is_safe"]:
        st.markdown(f'<div class="seq">Safe sequence: {alg.format_sequence(res["safe_sequence"])}</div>',
                    unsafe_allow_html=True)
    st.write(res["reason"])
    with st.expander("Show algorithm steps"):
        for s in res["steps"]:
            st.markdown(f"- {s}")


def state_tables(state, prefix=""):
    n, m = len(state["allocation"]), len(state["available"])
    pn, rn = alg.process_names(n), alg.resource_names(m)
    show_table(prefix + "Available", [state["available"]], ["Available"], rn)
    show_table(prefix + "Allocation", state["allocation"], pn, rn)
    if state.get("need") is not None:
        show_table(prefix + "Need", state["need"], pn, rn)


def render_request_result(r):
    st.markdown(badge(r["status"]), unsafe_allow_html=True)
    st.write(r["message"])
    if r["status"] != alg.INVALID:
        c1, c2 = st.columns(2)
        with c1:
            state_tables(r["original_state"], "Original ")
        with c2:
            if r["status"] == alg.DENIED_UNSAFE and r["tentative_state"]:
                state_tables(r["tentative_state"], "Tentative (if granted) ")
            else:
                state_tables(r["final_state"], "Final ")
        if r["status"] == alg.DENIED_UNSAFE:
            st.info("Rollback: the original Allocation, Available and Need are restored exactly.")
            state_tables(r["final_state"], "After rollback - ")
        st.caption("State unchanged: " + ("YES" if r["state_unchanged"] else "NO (request was committed)"))
    with st.expander("Show request-checking steps"):
        for s in r["steps"]:
            st.markdown(f"- {s}")


def render_result(res, nested=False):
    if "subtests" in res:
        st.markdown(badge(res["actual"] if res["passed"] else res["actual"]), unsafe_allow_html=True)
        for sub in res["subtests"]:
            mark = "✔" if sub["passed"] else "✖"
            with st.expander(f"{mark} {sub['id']} - {sub['title']}  →  {sub['actual']}"):
                render_result(sub, nested=True)
        return
    st.markdown(f"**Calculated result:** {badge(res['actual'])}", unsafe_allow_html=True)
    st.caption(f"Expected: {res['expected']} · Matches expected: {'YES' if res['passed'] else 'NO'}")
    st.markdown("**Input:** " + " · ".join(res["inputs"]))
    st.write(res["explanation"])
    for label, value in res["details"]:
        st.markdown(f"- **{label}:** {value}")
    if res["state_unchanged"] is not None:
        st.caption("Original state unchanged: " + ("YES" if res["state_unchanged"] else "NO"))
    if res["tables"]:
        cols = st.columns(2)
        for k, t in enumerate(res["tables"]):
            with cols[k % 2]:
                show_table(t["title"], t["rows"], t["index"], t["columns"])
    if res["steps"]:
        if nested:
            st.markdown("**Steps:**")
            for s in res["steps"]:
                st.markdown(f"- {s}")
        else:
            with st.expander("Show steps"):
                for s in res["steps"]:
                    st.markdown(f"- {s}")


def render_detection(d):
    st.markdown(badge(d["status"]), unsafe_allow_html=True)
    if d["status"] == alg.INVALID:
        st.error(d["reason"])
        return
    if d["finish_order"]:
        st.write("Processes that can finish: " + alg.format_sequence(d["finish_order"]))
    if d["deadlocked"]:
        st.write("Processes that cannot finish: " + ", ".join(f"P{i}" for i in d["deadlocked"]))
    st.write(d["reason"])
    with st.expander("Show detection steps"):
        for s in d["steps"]:
            st.markdown(f"- {s}")


# ------------------------------------------------------------------ editors
def editable_state():
    c1, c2 = st.columns(2)
    n = c1.number_input("Number of processes", 1, 10, value=len(ss.allocation), step=1, key=f"n_{ss.ver}")
    m = c2.number_input("Number of resource types", 1, 6, value=len(ss.available), step=1, key=f"m_{ss.ver}")
    if resize_state(int(n), int(m)):
        st.rerun()
    pn, rn = alg.process_names(len(ss.allocation)), alg.resource_names(len(ss.available))
    st.markdown("**Available vector** (edit cells directly)")
    av = st.data_editor(pd.DataFrame([ss.available], index=["Available"], columns=rn), key=f"av_{ss.ver}")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Allocation matrix**")
        al = st.data_editor(pd.DataFrame(ss.allocation, index=pn, columns=rn), key=f"al_{ss.ver}")
    with c2:
        st.markdown("**Maximum demand matrix**")
        mx = st.data_editor(pd.DataFrame(ss.maximum, index=pn, columns=rn), key=f"mx_{ss.ver}")
    ss.available = df_to_matrix(av)[0]
    ss.allocation = df_to_matrix(al)
    ss.maximum = df_to_matrix(mx)


def submit_request():
    pid = ss[f"req_proc_{ss.ver}"]
    m = len(ss.available)
    req = [ss[f"req_{ss.ver}_{j}"] for j in range(m)]
    result = alg.request_resources(pid, req, ss.available, ss.allocation, ss.maximum)
    if result["granted"] and not result["no_op"]:
        fs = result["final_state"]            # commit the granted request to the dashboard
        load_state(fs["available"], fs["allocation"], fs["maximum"])
    ss.last_request = result


# ------------------------------------------------------------------ pages
def page_dashboard():
    st.markdown('<div class="hero"><h1>Deadlock Analysis and Resource Allocation Dashboard</h1>'
                '<p>Operating Systems project: Banker\'s Algorithm, deadlock detection, recovery and '
                'prevention - all calculated live from your inputs.</p></div>', unsafe_allow_html=True)
    res = current_status()
    c = st.columns(4)
    with c[0]:
        card("Processes", len(ss.allocation))
    with c[1]:
        card("Resource types", len(ss.available))
    with c[2]:
        card("Available", str(ss.available))
    with c[3]:
        st.markdown(f'<div class="card"><div class="lbl">Current system status</div>'
                    f'<div style="margin-top:.5rem">{badge(res["status"])}</div></div>', unsafe_allow_html=True)
    st.write("")
    st.markdown("### What is a safe state?")
    st.write("A state is **SAFE** if there is at least one order (a *safe sequence*) in which every "
             "process can get its maximum resources, finish and release them. **UNSAFE** means no such "
             "order exists - the system *might* deadlock, but an unsafe state is not the same as a "
             "deadlock that has already happened.")
    st.markdown("**Status labels:** SAFE · UNSAFE · DEADLOCK DETECTED · "
                "REQUEST DENIED: INSUFFICIENT RESOURCES · INVALID INPUT")
    b = st.columns(5)
    b[0].button("Check Safe State →", on_click=go, args=("Check Safe State",))
    b[1].button("Request Resources →", on_click=go, args=("Request Resources",))
    b[2].button("Deadlock Lab →", on_click=go, args=("Deadlock Lab",))
    b[3].button("Load sample (TC1)", on_click=cb_load, args=(tc.TC1_DATA,))
    b[4].button("Load sample (TC3)", on_click=cb_load, args=(tc.TC3_DATA,))


def page_safe():
    st.header("Check Safe State")
    st.caption("Need = Maximum − Allocation")
    b = st.columns(4)
    b[0].button("Load TC1 data", on_click=cb_load, args=(tc.TC1_DATA,), key="b_tc1")
    b[1].button("Load TC3 data", on_click=cb_load, args=(tc.TC3_DATA,), key="b_tc3")
    editable_state()
    ok, errors = alg.validate_input(ss.available, ss.allocation, ss.maximum)
    if ok:
        pn, rn = alg.process_names(len(ss.allocation)), alg.resource_names(len(ss.available))
        show_table("Need matrix (Maximum − Allocation)", alg.calculate_need(ss.maximum, ss.allocation), pn, rn)
    else:
        st.markdown(badge(alg.INVALID), unsafe_allow_html=True)
        for e in errors:
            st.error(e)
    if st.button("Check Safe State", type="primary"):
        render_safety(alg.check_safe_state(ss.available, ss.allocation, ss.maximum))


def page_request():
    st.header("Request Resources")
    ok, errors = alg.validate_input(ss.available, ss.allocation, ss.maximum)
    if not ok:
        st.markdown(badge(alg.INVALID), unsafe_allow_html=True)
        for e in errors:
            st.error(e)
        st.info("Fix the data on the 'Check Safe State' page first.")
        return
    n, m = len(ss.allocation), len(ss.available)
    pn, rn = alg.process_names(n), alg.resource_names(m)
    state_tables({"available": ss.available, "allocation": ss.allocation,
                  "need": alg.calculate_need(ss.maximum, ss.allocation)}, "Current ")
    st.markdown("#### Make a request")
    st.selectbox("Process", list(range(n)), format_func=lambda i: pn[i], key=f"req_proc_{ss.ver}")
    cols = st.columns(m)
    for j in range(m):
        cols[j].number_input(f"Request {rn[j]}", min_value=-20, max_value=50, value=0, step=1,
                             key=f"req_{ss.ver}_{j}")
    st.button("Submit Request", type="primary", on_click=submit_request)
    st.caption("A granted request is committed to the dashboard state; a denied one changes nothing. "
               "Negative values are allowed in the box only so you can see them rejected.")
    if ss.get("last_request"):
        render_request_result(ss.last_request)


def page_lab():
    st.header("Deadlock Detection, Recovery, Prevention & Test Lab")
    t1, t2, t3, t4 = st.tabs(["Detection", "Recovery", "Prevention", "Test Lab"])
    d = ss.det
    n, m = len(d["allocation"]), len(d["available"])
    pn, rn = alg.process_names(n), alg.resource_names(m)

    with t1:
        st.write("Detection uses **Available, Allocation and the outstanding Request matrix** "
                 "(what each process is waiting for now) - *not* the Banker's Need matrix.")
        av = st.data_editor(pd.DataFrame([d["available"]], index=["Available"], columns=rn),
                            key=f"dav_{ss.det_ver}")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**Allocation**")
            al = st.data_editor(pd.DataFrame(d["allocation"], index=pn, columns=rn), key=f"dal_{ss.det_ver}")
        with c2:
            st.markdown("**Outstanding Request**")
            rq = st.data_editor(pd.DataFrame(d["request"], index=pn, columns=rn), key=f"drq_{ss.det_ver}")
        d["available"], d["allocation"], d["request"] = df_to_matrix(av)[0], df_to_matrix(al), df_to_matrix(rq)
        st.button("Reset to TC4 data", on_click=cb_load_det)
        if st.button("Run deadlock detection", type="primary"):
            res = alg.detect_deadlock(d["available"], d["allocation"], d["request"])
            render_detection(res)
            with st.expander("Assumptions of this algorithm"):
                for a in res["assumptions"]:
                    st.markdown(f"- {a}")

    with t2:
        st.write("Pick a process to **terminate (simulation only)**. Its allocation is released and "
                 "detection is run again on the data from the Detection tab.")
        victim = st.selectbox("Process to terminate", list(range(n)), format_func=lambda i: pn[i], key="victim")
        if st.button("Terminate and re-run detection", type="primary"):
            r = alg.recover_from_deadlock(victim, d["available"], d["allocation"], d["request"])
            if r["status"] == alg.INVALID:
                st.markdown(badge(alg.INVALID), unsafe_allow_html=True)
                st.error(r["reason"])
            else:
                st.markdown(f"Before: {badge(r['before']['status'])} → After: {badge(r['after']['status'])}",
                            unsafe_allow_html=True)
                st.write(r["reason"])
                st.write(f"Released {r['released']} → Available = {r['new_available']}")
                with st.expander("Show steps"):
                    for s in r["steps"]:
                        st.markdown(f"- {s}")
                st.warning(r["note"])

    with t3:
        st.write("**Fixed resource ordering:** a process may request resources only in increasing "
                 "order. Since everyone climbs the same ladder, a circular wait can never form.")
        order_text = st.text_input("Resource order (comma separated)", "A, B, C")
        order = [x.strip().upper() for x in order_text.split(",") if x.strip()]
        if len(order) >= 2 and len(set(order)) == len(order):
            held = st.multiselect("Resources the process already holds", order)
            req = st.selectbox("Resource it now requests", order)
            if st.button("Check request against the order", type="primary"):
                r = alg.check_resource_order(order, held, req)
                st.markdown(badge(r["status"]), unsafe_allow_html=True)
                st.write(r["reason"])
        else:
            st.error("Enter at least two different resource names, e.g. A, B, C.")
        st.caption("This is a separate prevention strategy - it is not Banker's Algorithm.")

    with t4:
        choice = st.selectbox("Choose a test case", list(tc.TEST_CASES),
                              format_func=lambda k: f"{k} - {tc.TEST_CASES[k]['title']}")
        c1, c2 = st.columns(2)
        run = c1.button("Run test case", type="primary")
        state = tc.TEST_CASES[choice]["state"]
        if state:
            c2.button("Load this data into the dashboard", on_click=cb_load, args=(state,))
        if run:
            ss.lab_result = (choice, tc.TEST_CASES[choice]["run"]())
        if ss.get("lab_result") and ss.lab_result[0] == choice:
            render_result(ss.lab_result[1])


# ------------------------------------------------------------------ router
st.sidebar.title("🔒 Deadlock Dashboard")
st.sidebar.radio("Go to", PAGES, key="page")
st.sidebar.caption("All results are calculated live by algorithms.py.")
{"Dashboard": page_dashboard, "Check Safe State": page_safe,
 "Request Resources": page_request, "Deadlock Lab": page_lab}[ss.page]()
