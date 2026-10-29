"""
test_cases.py - sample scenarios TC1-TC6 and runners that execute the REAL algorithms.
Each run_tcX() returns a result dict that both the dashboard and pytest use.
"""
import copy
import algorithms as alg

# ------------------------------------------------------------------ data
TC1_DATA = {
    "available": [3, 3, 2],
    "allocation": [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
    "maximum": [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]],
}
TC2_REQUEST = (0, [0, 4, 0])
TC3_DATA = {"available": [1], "allocation": [[0], [1]], "maximum": [[2], [2]]}
TC3_REQUEST = (0, [1])
TC4_DATA = {"available": [0, 0], "allocation": [[1, 0], [0, 1]], "request": [[0, 1], [1, 0]]}
TC5_ORDER = ["A", "B", "C"]


# ------------------------------------------------------------------ helpers
def _table(title, matrix, rows, cols):
    return {"title": title, "rows": copy.deepcopy(matrix), "index": rows, "columns": cols}


def _result(tc_id, title, expected, actual, explanation, inputs, tables=None, steps=None,
            state_unchanged=None, details=None):
    return {"id": tc_id, "title": title, "expected": expected, "actual": actual,
            "passed": expected == actual, "explanation": explanation, "inputs": inputs,
            "tables": tables or [], "steps": steps or [],
            "state_unchanged": state_unchanged, "details": details or []}


def _state_tables(state, prefix=""):
    n, m = len(state["allocation"]), len(state["available"])
    pn, rn = alg.process_names(n), alg.resource_names(m)
    tables = [_table(prefix + "Available", [state["available"]], ["Available"], rn),
              _table(prefix + "Allocation", state["allocation"], pn, rn)]
    if state.get("need") is not None:
        tables.append(_table(prefix + "Need", state["need"], pn, rn))
    return tables


# ------------------------------------------------------------------ TC1
def run_tc1():
    d = TC1_DATA
    res = alg.check_safe_state(d["available"], d["allocation"], d["maximum"])
    n, rn, pn = 5, alg.resource_names(3), alg.process_names(5)
    tables = [_table("Available", [d["available"]], ["Available"], rn),
              _table("Allocation", d["allocation"], pn, rn),
              _table("Maximum", d["maximum"], pn, rn),
              _table("Need (Max − Alloc)", res["need"], pn, rn)]
    return _result("TC1", "Safe state using Banker's Algorithm", alg.SAFE, res["status"],
                   res["reason"], ["Available = [3, 3, 2]", "Allocation and Maximum as in the table"],
                   tables, res["steps"],
                   details=[("Safe sequence", alg.format_sequence(res["safe_sequence"]))])


# ------------------------------------------------------------------ TC2
def run_tc2():
    d = copy.deepcopy(TC1_DATA)
    pid, req = TC2_REQUEST
    res = alg.request_resources(pid, req, d["available"], d["allocation"], d["maximum"])
    need_p0 = res["original_state"]["need"][0]
    return _result("TC2", "Request exceeds Available resources", alg.DENIED_AVAILABLE, res["status"],
                   f"P0 Need = {need_p0}, so [0, 4, 0] is within Need, but Available is "
                   f"{d['available']} and only 3 units of B exist. {res['message']}",
                   [f"Process: P0", f"Request = {req}", "Same initial data as TC1"],
                   _state_tables(res["original_state"], "Original "), res["steps"],
                   state_unchanged=res["state_unchanged"])


# ------------------------------------------------------------------ TC3
def run_tc3():
    d = copy.deepcopy(TC3_DATA)
    before = copy.deepcopy(d)
    initial = alg.check_safe_state(d["available"], d["allocation"], d["maximum"])
    pid, req = TC3_REQUEST
    res = alg.request_resources(pid, req, d["available"], d["allocation"], d["maximum"])
    restored = (d == before and res["final_state"]["allocation"] == [[0], [1]]
                and res["final_state"]["available"] == [1])
    tentative = res["tentative_state"]
    tables = _state_tables(res["original_state"], "Original ")
    if tentative:
        tables += _state_tables(tentative, "If granted ")
    details = [("Initial state", f"{initial['status']} ({alg.format_sequence(initial['safe_sequence'])})"),
               ("After rollback", f"P0 Allocation = {res['final_state']['allocation'][0]}, "
                                  f"P1 Allocation = {res['final_state']['allocation'][1]}, "
                                  f"Available = {res['final_state']['available']}")]
    return _result("TC3", "Within Need and Available, but UNSAFE", alg.DENIED_UNSAFE, res["status"],
                   "P0 asks for 1 unit: that is within its Need (2) and Available (1). But after "
                   "granting it Available = [0] and both processes still need 1 more, so neither "
                   "can finish → unsafe. Banker's Algorithm denies it and rolls back. "
                   f"Original state restored exactly: {'yes' if restored else 'NO'}.",
                   ["Total instances of A = 2", "P0: Allocation 0, Maximum 2", "P1: Allocation 1, Maximum 2",
                    "Available = [1]", "P0 requests [1]"],
                   tables, res["steps"], state_unchanged=restored and res["state_unchanged"],
                   details=details)


# ------------------------------------------------------------------ TC4
def run_tc4():
    d = copy.deepcopy(TC4_DATA)
    det = alg.detect_deadlock(d["available"], d["allocation"], d["request"])
    rec = alg.recover_from_deadlock(0, d["available"], d["allocation"], d["request"])
    rn, pn = alg.resource_names(2), alg.process_names(2)
    tables = [_table("Available", [d["available"]], ["Available"], rn),
              _table("Allocation", d["allocation"], pn, rn),
              _table("Outstanding Request", d["request"], pn, rn)]
    steps = (["DETECTION:"] + det["steps"] + ["RECOVERY (terminate P0):"] + rec["steps"])
    both = det["status"] == alg.DEADLOCK and rec["recovered"]
    actual = alg.DEADLOCK if both else det["status"]
    return _result("TC4", "Genuine deadlock detection and recovery", alg.DEADLOCK, actual,
                   "P0 holds A and waits for B; P1 holds B and waits for A (circular wait). "
                   f"Deadlocked: {', '.join('P' + str(i) for i in det['deadlocked'])}. "
                   f"Recovery: {rec['reason']} {rec['note']}",
                   ["Available = [0, 0]", "One instance each of A and B"], tables, steps,
                   details=[("After terminating P0", f"Available = {rec['new_available']}"),
                            ("Detection re-run", rec["after"]["status"]),
                            ("Finish order", alg.format_sequence(rec["after"]["finish_order"]))])


# ------------------------------------------------------------------ TC5
def run_tc5():
    checks = [([], "A"), (["A"], "B"), (["B"], "A")]
    outs = [alg.check_resource_order(TC5_ORDER, h, r) for h, r in checks]
    steps = [f"Holds {h or 'nothing'} → requests {r}: {o['status']}. {o['reason']}"
             for (h, r), o in zip(checks, outs)]
    ok = [o["status"] for o in outs] == [alg.ALLOWED, alg.ALLOWED, alg.REJECTED]
    actual = alg.REJECTED if ok else "UNEXPECTED"
    return _result("TC5", "Prevention with fixed resource ordering", alg.REJECTED, actual,
                   "Resources must be requested in increasing order A → B → C. A process holding "
                   "B may not request A. Because every process climbs the same order, a cycle of "
                   "waiting processes can never form, so circular wait (one of the four necessary "
                   "conditions) is impossible. This is a prevention policy, not Banker's Algorithm.",
                   ["Order: A → B → C", "1) request A  2) then request B  3) holding B, request A"],
                   [], steps, details=[("Results", " | ".join(o["status"] for o in outs))])


# ------------------------------------------------------------------ TC6
def _sub(sub_id, title, expected, actual, inputs, reason, unchanged, extra=None):
    r = _result(sub_id, title, expected, actual, reason, inputs, state_unchanged=unchanged,
                details=extra)
    return r


def run_tc6():
    subs = []

    av, al, mx = [0], [[1]], [[1]]                      # A
    r = alg.check_safe_state(av, al, mx)
    subs.append(_sub("TC6-A", "Zero Available, zero Need", alg.SAFE, r["status"],
                     ["Available = [0]", "Allocation = [1]", "Maximum = [1] → Need = [0]"],
                     "The process needs nothing more, so it can finish even with zero Available.", True,
                     [("Safe sequence", alg.format_sequence(r["safe_sequence"]))]))

    av, al, mx = [1], [[0]], [[1]]                      # B
    r = alg.request_resources(0, [0], av, al, mx)
    subs.append(_sub("TC6-B", "Zero resource request", alg.GRANTED, r["status"],
                     ["Available = [1]", "Allocation = [0], Maximum = [1]", "P0 requests [0]"],
                     r["message"], r["state_unchanged"], [("No-op", str(r["no_op"]))]))

    r = alg.request_resources(9, [1], av, al, mx)       # C
    subs.append(_sub("TC6-C", "Invalid process ID", alg.INVALID, r["status"],
                     ["Only P0 exists", "Request for P9 = [1]"], r["message"], r["state_unchanged"]))

    r = alg.request_resources(0, [-1], av, al, mx)      # D
    subs.append(_sub("TC6-D", "Negative request", alg.INVALID, r["status"],
                     ["P0 requests [-1]"], r["message"], r["state_unchanged"]))

    av, al, mx = [1], [[1]], [[2]]                      # E
    r = alg.request_resources(0, [2], av, al, mx)
    subs.append(_sub("TC6-E", "Request exceeds Need", alg.DENIED_NEED, r["status"],
                     ["Need = [1] (Max 2 − Alloc 1)", "P0 requests [2]"], r["message"],
                     r["state_unchanged"]))

    r = alg.check_safe_state([1], [[2]], [[1]])         # F
    subs.append(_sub("TC6-F", "Allocation exceeds Maximum", alg.INVALID, r["status"],
                     ["Allocation = [2]", "Maximum = [1]"], r["reason"], True))

    av, al, mx = [0], [[0]], [[1]]                      # G
    r = alg.request_resources(0, [1], av, al, mx)
    subs.append(_sub("TC6-G", "Resources unavailable", alg.DENIED_AVAILABLE, r["status"],
                     ["Available = [0]", "Need = [1]", "P0 requests [1]"],
                     r["message"] + " This alone is NOT a confirmed deadlock.", r["state_unchanged"]))

    passed = all(s["passed"] for s in subs)
    return {"id": "TC6", "title": "Boundary cases and invalid inputs", "subtests": subs,
            "passed": passed, "actual": "ALL SUBTESTS MATCH" if passed else "SOME SUBTESTS FAILED",
            "expected": "ALL SUBTESTS MATCH", "explanation": "Seven separate subtests; not every case is an error."}


TEST_CASES = {
    "TC1": {"title": "Safe state (Banker's)", "run": run_tc1, "state": TC1_DATA},
    "TC2": {"title": "Request exceeds Available", "run": run_tc2, "state": TC1_DATA},
    "TC3": {"title": "Unsafe resulting state + rollback", "run": run_tc3, "state": TC3_DATA},
    "TC4": {"title": "Deadlock detection and recovery", "run": run_tc4, "state": None},
    "TC5": {"title": "Fixed resource ordering", "run": run_tc5, "state": None},
    "TC6": {"title": "Boundary cases and invalid inputs", "run": run_tc6, "state": None},
}
