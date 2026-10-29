"""
algorithms.py - all deadlock logic for the project (no Streamlit code here).

Rules followed everywhere in this file:
  * Functions NEVER modify the lists that are passed in (they work on copies).
  * Bad input never crashes: it returns status INVALID INPUT with messages.
"""
import copy
import numbers

# ---------------------------------------------------------------- status labels
SAFE = "SAFE"
UNSAFE = "UNSAFE"
DEADLOCK = "DEADLOCK DETECTED"
NO_DEADLOCK = "NO DEADLOCK"
GRANTED = "REQUEST GRANTED"
DENIED_NEED = "REQUEST DENIED: EXCEEDS NEED"
DENIED_AVAILABLE = "REQUEST DENIED: INSUFFICIENT RESOURCES"
DENIED_UNSAFE = "REQUEST DENIED: UNSAFE RESULTING STATE"
INVALID = "INVALID INPUT"
ALLOWED = "ALLOWED"
REJECTED = "REJECTED: VIOLATES RESOURCE ORDER"


# ---------------------------------------------------------------- small helpers
def process_names(n):
    return [f"P{i}" for i in range(n)]


def resource_names(m):
    return [chr(ord("A") + j) if j < 26 else f"R{j}" for j in range(m)]


def format_sequence(sequence):
    return " → ".join(f"P{i}" for i in sequence)


def _is_int(value):
    return isinstance(value, numbers.Integral) and not isinstance(value, bool)


def _check_vector(name, vec, length, errors):
    if not isinstance(vec, (list, tuple)):
        errors.append(f"{name} must be a list of whole numbers.")
        return
    if length is not None and len(vec) != length:
        errors.append(f"{name} has {len(vec)} values but {length} were expected.")
        return
    for j, v in enumerate(vec):
        if not _is_int(v):
            errors.append(f"{name}[{resource_names(j + 1)[j]}] = {v!r} is not a whole number.")
        elif v < 0:
            errors.append(f"{name}[{resource_names(j + 1)[j]}] = {v} is negative (not allowed).")


def _check_matrix(name, mat, n, m, errors):
    if not isinstance(mat, (list, tuple)):
        errors.append(f"{name} must be a list of rows.")
        return
    if len(mat) != n:
        errors.append(f"{name} has {len(mat)} rows but {n} processes were expected.")
        return
    for i, row in enumerate(mat):
        _check_vector(f"{name} row P{i}", row, m, errors)


def calculate_need(maximum, allocation):
    """Need = Maximum - Allocation (element by element)."""
    return [[maximum[i][j] - allocation[i][j] for j in range(len(maximum[i]))]
            for i in range(len(maximum))]


def validate_input(available, allocation, maximum):
    """Check a Banker's state. Returns (is_valid, list_of_error_messages)."""
    errors = []
    if not isinstance(available, (list, tuple)) or len(available) == 0:
        return False, ["Available must be a non-empty list of whole numbers."]
    m = len(available)
    _check_vector("Available", available, m, errors)
    if not isinstance(allocation, (list, tuple)) or len(allocation) == 0:
        errors.append("Allocation must be a non-empty list of rows (at least one process).")
        return False, errors
    n = len(allocation)
    _check_matrix("Allocation", allocation, n, m, errors)
    _check_matrix("Maximum", maximum, n, m, errors)
    if not errors:  # only compare values when the shapes/types are fine
        for i in range(n):
            for j in range(m):
                if allocation[i][j] > maximum[i][j]:
                    errors.append(
                        f"Allocation of P{i} for resource {resource_names(m)[j]} "
                        f"({allocation[i][j]}) exceeds its Maximum ({maximum[i][j]}).")
    return len(errors) == 0, errors


def validate_detection_input(available, allocation, request_matrix):
    """Check the data used by the deadlock-detection algorithm."""
    errors = []
    if not isinstance(available, (list, tuple)) or len(available) == 0:
        return False, ["Available must be a non-empty list of whole numbers."]
    m = len(available)
    _check_vector("Available", available, m, errors)
    if not isinstance(allocation, (list, tuple)) or len(allocation) == 0:
        errors.append("Allocation must be a non-empty list of rows.")
        return False, errors
    n = len(allocation)
    _check_matrix("Allocation", allocation, n, m, errors)
    _check_matrix("Request", request_matrix, n, m, errors)
    return len(errors) == 0, errors


# ---------------------------------------------------------------- Banker's safety
def check_safe_state(available, allocation, maximum):
    """Banker's safety algorithm. Returns a dict (status, safe_sequence, steps, reason...)."""
    ok, errors = validate_input(available, allocation, maximum)
    if not ok:
        return {"status": INVALID, "is_safe": False, "safe_sequence": [], "steps": [],
                "reason": " ".join(errors), "errors": errors, "need": None}

    n, m = len(allocation), len(available)
    need = calculate_need(maximum, allocation)
    work = list(available)
    finish = [False] * n
    sequence = []
    steps = [f"Start: Work = Available = {work}. No process is finished yet."]

    progress = True
    while progress:                      # keep scanning until a full pass finds nobody
        progress = False
        for i in range(n):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(m)):
                new_work = [work[j] + allocation[i][j] for j in range(m)]
                steps.append(f"P{i}: Need {need[i]} ≤ Work {work}, so P{i} can finish. "
                             f"It releases Allocation {allocation[i]} → Work = {new_work}.")
                work, finish[i] = new_work, True
                sequence.append(i)
                progress = True

    if all(finish):
        reason = (f"Every process can finish in the order {format_sequence(sequence)}, "
                  "so a safe sequence exists and the state is SAFE.")
        steps.append("All processes finished → SAFE.")
        return {"status": SAFE, "is_safe": True, "safe_sequence": sequence, "steps": steps,
                "reason": reason, "errors": [], "need": need}

    stuck = [i for i in range(n) if not finish[i]]
    steps.append(f"No unfinished process has Need ≤ Work {work}. "
                 f"Stuck: {', '.join('P' + str(i) for i in stuck)} → UNSAFE.")
    reason = (f"No safe sequence exists: {', '.join('P' + str(i) for i in stuck)} cannot be "
              "guaranteed to finish. The state is UNSAFE - this does NOT mean a deadlock has "
              "already happened; it means the system could run into one.")
    return {"status": UNSAFE, "is_safe": False, "safe_sequence": sequence, "steps": steps,
            "reason": reason, "errors": [], "need": need}


# ---------------------------------------------------------------- resource request
def _parse_process_id(process_id, n):
    if isinstance(process_id, str):
        s = process_id.strip().upper()
        s = s[1:] if s.startswith("P") else s
        if not s.isdigit():
            return None
        process_id = int(s)
    if _is_int(process_id) and 0 <= process_id < n:
        return int(process_id)
    return None


def _snapshot(available, allocation, maximum, valid):
    snap = {"available": copy.deepcopy(available), "allocation": copy.deepcopy(allocation),
            "maximum": copy.deepcopy(maximum), "need": None}
    if valid:
        snap["need"] = calculate_need(maximum, allocation)
    return snap


def _req_result(status, message, steps, process, request, orig, final=None,
                tentative=None, safety=None, no_op=False):
    final = orig if final is None else final
    return {"status": status, "granted": status == GRANTED, "message": message,
            "steps": steps, "process": process, "request": request,
            "original_state": orig, "final_state": final, "tentative_state": tentative,
            "safety_result": safety, "no_op": no_op,
            "state_unchanged": final == orig}


def request_resources(process_id, request, available, allocation, maximum):
    """Banker's resource-request algorithm. Inputs are never modified.

    The returned dict has 'final_state'; the CALLER decides whether to adopt it.
    """
    steps = []
    ok, errors = validate_input(available, allocation, maximum)
    orig = _snapshot(available, allocation, maximum, ok)
    if not ok:
        return _req_result(INVALID, "The system state is invalid. " + " ".join(errors),
                           ["State validation failed."], None, request, orig)

    n, m = len(allocation), len(available)
    rn = resource_names(m)

    pid = _parse_process_id(process_id, n)
    if pid is None:
        return _req_result(INVALID, f"Process {process_id!r} does not exist "
                           f"(valid processes: P0 to P{n - 1}).",
                           ["Step 1 failed: invalid process ID."], None, request, orig)
    name = f"P{pid}"
    steps.append(f"Step 1 OK: {name} is a valid process.")

    errs = []
    _check_vector("Request", request, m, errs)
    if errs:
        msg = " ".join(errs)
        if any("negative" in e for e in errs):
            msg = "Resource requests cannot be negative. " + msg
        return _req_result(INVALID, msg, steps + ["Step 2 failed: request is not valid."],
                           name, request, orig)
    steps.append(f"Step 2 OK: request {list(request)} has no negative values.")

    need = orig["need"]
    for j in range(m):
        if request[j] > need[pid][j]:
            return _req_result(
                DENIED_NEED,
                f"{name} asked for {request[j]} of {rn[j]} but its remaining Need is only "
                f"{need[pid][j]} (Maximum − Allocation). It would exceed its declared maximum claim.",
                steps + ["Step 3 failed: request > Need."], name, list(request), orig)
    steps.append(f"Step 3 OK: request ≤ Need {need[pid]}.")

    for j in range(m):
        if request[j] > available[j]:
            return _req_result(
                DENIED_AVAILABLE,
                f"{name} asked for {request[j]} of {rn[j]} but only {available[j]} are "
                "available right now. The request must wait. (This is not a deadlock, and "
                "the safety algorithm was not needed.)",
                steps + ["Step 4 failed: request > Available."], name, list(request), orig)
    steps.append(f"Step 4 OK: request ≤ Available {list(available)}.")

    if all(v == 0 for v in request):
        return _req_result(GRANTED, f"A zero request from {name} is accepted as a no-op. "
                           "The state is unchanged.", steps + ["Zero request → no change."],
                           name, list(request), orig, no_op=True)

    new_avail = [available[j] - request[j] for j in range(m)]
    new_alloc = copy.deepcopy(allocation)
    for j in range(m):
        new_alloc[pid][j] += request[j]
    tentative = _snapshot(new_avail, new_alloc, maximum, True)
    steps.append(f"Step 5: pretend to grant. Available → {new_avail}, "
                 f"{name} Allocation → {new_alloc[pid]}. Running the safety algorithm...")
    safety = check_safe_state(new_avail, new_alloc, maximum)

    if safety["is_safe"]:
        steps.append(f"Step 6: resulting state is SAFE ({format_sequence(safety['safe_sequence'])}) → grant.")
        return _req_result(GRANTED, f"Granted. The resulting state is safe: "
                           f"{format_sequence(safety['safe_sequence'])}.", steps, name,
                           list(request), orig, final=tentative, tentative=tentative, safety=safety)

    steps.append("Step 6: resulting state is UNSAFE → deny and roll back to the original state.")
    return _req_result(DENIED_UNSAFE,
                       "Denied. The request fits within Need and Available, but granting it would "
                       "leave the system in an UNSAFE state. The original state was restored exactly.",
                       steps, name, list(request), orig, tentative=tentative, safety=safety)


# ---------------------------------------------------------------- deadlock detection
DETECTION_ASSUMPTIONS = [
    "Each resource type has a fixed number of identical instances.",
    "Resources are not preemptable - a process only gives them back when it finishes.",
    "A process that is not waiting will finish and then release everything it holds.",
    "A process holding no resources is treated as finished (nobody waits on it).",
    "The matrix used is the outstanding Request matrix (what each process is waiting for "
    "right now), NOT the Banker's Need matrix.",
]


def detect_deadlock(available, allocation, outstanding_request):
    """Deadlock detection using Available, Allocation and the outstanding Request matrix."""
    ok, errors = validate_detection_input(available, allocation, outstanding_request)
    if not ok:
        return {"status": INVALID, "deadlocked": [], "finish_order": [], "steps": [],
                "reason": " ".join(errors), "errors": errors,
                "assumptions": DETECTION_ASSUMPTIONS}

    n, m = len(allocation), len(available)
    work = list(available)
    finish = [all(a == 0 for a in allocation[i]) for i in range(n)]
    steps = [f"Start: Work = Available = {work}."]
    for i in range(n):
        if finish[i]:
            steps.append(f"P{i} holds nothing, so it is marked finished.")

    order = []
    progress = True
    while progress:
        progress = False
        for i in range(n):
            if not finish[i] and all(outstanding_request[i][j] <= work[j] for j in range(m)):
                new_work = [work[j] + allocation[i][j] for j in range(m)]
                steps.append(f"P{i}: Request {outstanding_request[i]} ≤ Work {work}, so it can "
                             f"finish and release {allocation[i]} → Work = {new_work}.")
                work, finish[i] = new_work, True
                order.append(i)
                progress = True

    deadlocked = [i for i in range(n) if not finish[i]]
    if deadlocked:
        names = ", ".join(f"P{i}" for i in deadlocked)
        steps.append(f"No remaining process can be satisfied with Work {work}.")
        reason = (f"{names} cannot finish: each is waiting for resources that only another "
                  "waiting process holds. Under the stated assumptions they are deadlocked.")
        status = DEADLOCK
    else:
        reason = "Every process can finish, so there is no deadlock."
        steps.append("All processes can finish → no deadlock.")
        status = NO_DEADLOCK
    return {"status": status, "deadlocked": deadlocked, "finish_order": order, "steps": steps,
            "reason": reason, "errors": [], "assumptions": DETECTION_ASSUMPTIONS}


# ---------------------------------------------------------------- deadlock recovery
def recover_from_deadlock(process_id, available, allocation, outstanding_request):
    """SIMULATION: terminate one process, release its resources, run detection again."""
    ok, errors = validate_detection_input(available, allocation, outstanding_request)
    if not ok:
        return {"status": INVALID, "recovered": False, "reason": " ".join(errors),
                "steps": [], "before": None, "after": None}
    n = len(allocation)
    pid = _parse_process_id(process_id, n)
    if pid is None:
        return {"status": INVALID, "recovered": False, "steps": [], "before": None,
                "after": None, "reason": f"Process {process_id!r} does not exist."}

    before = detect_deadlock(available, allocation, outstanding_request)
    released = list(allocation[pid])
    new_avail = [available[j] + released[j] for j in range(len(available))]
    new_alloc = copy.deepcopy(allocation)
    new_req = copy.deepcopy(outstanding_request)
    new_alloc[pid] = [0] * len(available)
    new_req[pid] = [0] * len(available)
    after = detect_deadlock(new_avail, new_alloc, new_req)

    steps = [f"Terminate P{pid} (simulation only).",
             f"Release its allocation {released} → Available becomes {new_avail}.",
             "Run the detection algorithm again on the reduced system."] + after["steps"]
    recovered = after["status"] == NO_DEADLOCK
    reason = ("Recovery worked: the remaining processes can now finish."
              if recovered else "Deadlock remains: terminating this process was not enough.")
    return {"status": after["status"], "recovered": recovered, "terminated": pid,
            "released": released, "new_available": new_avail, "new_allocation": new_alloc,
            "new_request": new_req, "before": before, "after": after, "steps": steps,
            "reason": reason,
            "note": "This is only a simulation. A real OS must also consider lost work, "
                    "data consistency, process priority and restart cost."}


# ---------------------------------------------------------------- prevention (resource ordering)
def check_resource_order(resource_order, held, requested):
    """Allow a request only if `requested` comes AFTER every resource already held."""
    if (not isinstance(resource_order, (list, tuple)) or len(resource_order) == 0
            or len(set(resource_order)) != len(resource_order)):
        return {"status": INVALID, "allowed": False,
                "reason": "The resource order must be a non-empty list without duplicates."}
    if requested not in resource_order or any(h not in resource_order for h in held):
        return {"status": INVALID, "allowed": False,
                "reason": "Every resource must appear in the defined order."}
    if requested in held:
        return {"status": INVALID, "allowed": False,
                "reason": f"The process already holds {requested}."}

    order = " → ".join(resource_order)
    if not held:
        return {"status": ALLOWED, "allowed": True,
                "reason": f"The process holds nothing, so requesting {requested} is allowed (order {order})."}
    highest = max(held, key=resource_order.index)
    if resource_order.index(requested) > resource_order.index(highest):
        return {"status": ALLOWED, "allowed": True,
                "reason": f"{requested} comes after {highest} in the order {order}, so it is allowed."}
    return {"status": REJECTED, "allowed": False,
            "reason": f"The process holds {highest} and asks for {requested}, which comes earlier "
                      f"in the order {order}. Resources must be requested in increasing order."}
