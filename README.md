# Deadlock Analysis and Resource Allocation Dashboard

## 1. Introduction
An interactive Streamlit dashboard for an Operating Systems course. It demonstrates deadlock **avoidance** (Banker's Algorithm), **detection**, **recovery** and **prevention**. Every result is calculated live from the inputs; nothing is hard-coded.

## 2. Problem statement
When processes share limited resources, they can wait for each other forever (deadlock). The OS needs ways to avoid, detect, recover from, or prevent this.

## 3. Objectives
- Check safe/unsafe state and find a safe sequence.
- Grant or deny resource requests correctly (with exact rollback).
- Detect a real deadlock, simulate recovery, and demonstrate a prevention policy.
- Verify everything with six test cases and automated pytest tests.

## 4. Technologies
Python 3, Streamlit (UI), Pandas (tables), pytest (tests). NumPy and Plotly were **not** used - plain lists were simpler and no chart was needed.

## 5. What is deadlock?
A set of processes is deadlocked when each is waiting for a resource held by another process in the set, so none can ever continue.

## 6. Four necessary conditions
1. **Mutual exclusion** - a resource can be used by only one process at a time.
2. **Hold and wait** - a process holds resources while waiting for more.
3. **No preemption** - resources cannot be forcibly taken away.
4. **Circular wait** - a cycle of processes, each waiting for the next one's resource.

## 7. Prevention vs avoidance vs detection vs recovery
| Approach | Idea | In this project |
|---|---|---|
| Prevention | Make one of the 4 conditions impossible | Resource ordering (breaks circular wait) |
| Avoidance | Grant a request only if the system stays safe | Banker's Algorithm |
| Detection | Let deadlock happen, then find it | Detection with Request matrix |
| Recovery | Break a detected deadlock | Terminate a process (simulation) |

## 8. Banker's Algorithm
`Need = Maximum − Allocation`.
**Safety algorithm:** Work = Available. Repeatedly find an unfinished process with Need ≤ Work; add its Allocation to Work and mark it finished. If all finish, the state is **SAFE** (the order is the safe sequence); otherwise **UNSAFE**.
**Request algorithm (checked in this order):** valid process → request ≥ 0 → request ≤ Need → request ≤ Available → pretend to allocate → run safety algorithm → grant if safe, else deny and roll back.
*Unsafe ≠ deadlock:* unsafe only means a deadlock is possible.

## 9. Deadlock detection algorithm
Uses **Available, Allocation and the outstanding Request matrix** (not Need). Work = Available; a process holding nothing is treated as finished; repeatedly find an unfinished process whose Request ≤ Work, add its Allocation to Work. Processes that never finish are deadlocked.
**Assumptions:** fixed instances per resource, no preemption, non-waiting processes eventually finish and release resources.

## 10. Resource-ordering prevention
Order the resources, e.g. A → B → C. A process may only request a resource that comes *after* everything it already holds. Holding B and asking for A is rejected. Because all processes climb the same order, a cycle of waits is impossible, so **circular wait** cannot occur. This is not Banker's Algorithm.

## 11. Test cases
| Test | What it shows | Expected |
|---|---|---|
| TC1 | Classic 5-process, 3-resource data | SAFE (P1 → P3 → P4 → P0 → P2) |
| TC2 | P0 requests [0,4,0]; Need [7,4,3] but Available [3,3,2] | DENIED: insufficient resources |
| TC3 | 1 resource, P0 requests [1]; within Need and Available | DENIED: unsafe resulting state, rollback to Available [1] |
| TC4 | P0 holds A wants B; P1 holds B wants A | DEADLOCK DETECTED; terminate P0 → P1 finishes |
| TC5 | Order A→B→C: A ok, then B ok, holding B asks A | Rejected by prevention policy |
| TC6 | 7 boundary cases (A–G) | A safe, B no-op granted, C/D/F invalid, E denied (Need), G denied (Available) |

## 12. Installation and execution (Windows PowerShell)
```powershell
cd path\to\deadlock_dashboard
python -m pip install -r requirements.txt
python -m streamlit run app.py
```
Streamlit prints a link (usually http://localhost:8501) and opens it in your browser.

## 13. Testing (run in a second terminal)
```powershell
cd path\to\deadlock_dashboard
python -m pytest -v
```

## 14. Limitations and assumptions
- A teaching simulation; no real processes or OS resources are involved.
- Recovery only *simulates* termination; real systems must handle lost work, consistency and restarts.
- Detection assumes the conditions in section 9. Max 10 processes and 6 resource types in the UI.
- Granted requests in the Request page are committed to the dashboard state; denied ones change nothing.

## 15. Likely viva questions
1. **Safe vs unsafe state?** Safe: a sequence exists where all processes can finish. Unsafe: none exists.
2. **Is unsafe the same as deadlock?** No. Unsafe means deadlock *may* happen; deadlock means processes are already stuck.
3. **What is the Need matrix?** Maximum − Allocation: what a process may still request.
4. **Why deny a request that is within Need and Available?** If granting it makes the state unsafe (TC3).
5. **Why does detection use the Request matrix, not Need?** Request is what a process is waiting for *now*; Need is a worst-case future claim.
6. **Avoidance vs prevention?** Avoidance checks each request dynamically; prevention removes one of the four conditions in advance.
7. **How does resource ordering stop deadlock?** It makes circular wait impossible.
8. **How does recovery work here?** Terminate a process, release its resources, re-run detection.
9. **What is a safe sequence?** An order in which every process can finish using Available plus what earlier processes release.
10. **Why can a process with Need = 0 finish when Available = 0?** It requires nothing more (TC6-A).
11. **What happens to the state when a request is denied?** Nothing: the original state is restored exactly.
12. **Which condition does Banker's Algorithm need?** Processes must declare maximum claims in advance.

## 16. Six-minute demo plan
| Time | Action |
|---|---|
| 0:00–0:40 | Introduce the project; show the Dashboard cards and the "safe state" explanation |
| 0:40–1:40 | Deadlock Lab → Test Lab → TC1: show tables and safe sequence; expand the steps |
| 1:40–2:20 | TC2: within Need, exceeds Available → denied, state unchanged |
| 2:20–3:10 | TC3: unsafe resulting state; show tentative state and rollback |
| 3:10–4:20 | TC4: deadlock detected (P0, P1); then Recovery tab: terminate P0 → no deadlock; say it is a simulation |
| 4:20–5:00 | TC5: ordering allows A, B and rejects B→A; explain circular wait |
| 5:00–5:40 | TC6: open subtests; stress that not every case is an error |
| 5:40–6:00 | Summarise: avoidance, detection, recovery, prevention; mention pytest |

## 17. Responsible AI and verification
- **AI assistant used:** Claude (Anthropic) generated the first version of the code, tests and this README from my prompt.
- **AI-assisted parts:** all files in this project.
- **What I personally did:** *(edit this honestly before submitting - e.g. read every function in algorithms.py, traced TC1 by hand, ran the dashboard, changed some inputs.)*
- **Verification:** the algorithms were checked with `python -m pytest -v`, and I traced TC1 and TC3 by hand. *(Write your own pytest result here after running it on your machine.)*
- This project runs locally only; it is not deployed, and no performance results are claimed.

## Project files
- `app.py` - Streamlit interface (calls the functions below)
- `algorithms.py` - Banker's, request handling, detection, recovery, prevention, validation
- `test_cases.py` - TC1–TC6 data and runners
- `tests/test_algorithms.py` - pytest tests
- `requirements.txt`, `pytest.ini` (lets pytest find the modules), `.streamlit/config.toml` (dark navy/purple theme)
