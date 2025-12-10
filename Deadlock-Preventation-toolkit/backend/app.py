# app.py
import os
from flask import Flask, request, jsonify
from flask_cors import CORS

from analyzer_static import analyze_python_source
from monitor_runtime import RuntimeMonitor

app = Flask(__name__)
CORS(app)

monitor = RuntimeMonitor()  # global runtime monitor


# ---------- YOUR ORIGINAL BANKER + RAG ----------

def bankers_algorithm(P, R, alloc, maxd, avail):
    work = avail[:]              # copy
    finish = [False] * P

    need = [[0] * R for _ in range(P)]
    for i in range(P):
        for j in range(R):
            need[i][j] = maxd[i][j] - alloc[i][j]

    safe_sequence = []
    while True:
        progressed = False
        for i in range(P):
            if not finish[i]:
                can_run = all(need[i][j] <= work[j] for j in range(R))
                if can_run:
                    for j in range(R):
                        work[j] += alloc[i][j]
                    finish[i] = True
                    safe_sequence.append(f"P{i}")
                    progressed = True
        if not progressed:
            break

    safe = all(finish)
    return safe, safe_sequence if safe else []


def detect_deadlock_graph(P, R, alloc, maxd):
    total = P + R
    graph = [[] for _ in range(total)]
    need = [[maxd[i][j] - alloc[i][j] for j in range(R)] for i in range(P)]

    for p in range(P):
        for r in range(R):
            pNode = p
            rNode = P + r
            if alloc[p][r] > 0:
                graph[rNode].append(pNode)
            if need[p][r] > 0:
                graph[pNode].append(rNode)

    color = [0] * total  # 0 = unvisited, 1 = visiting, 2 = visited

    def dfs(u):
        color[u] = 1
        for v in graph[u]:
            if color[v] == 1:
                return True
            if color[v] == 0 and dfs(v):
                return True
        color[u] = 2
        return False

    for node in range(total):
        if color[node] == 0 and dfs(node):
            return True, graph
    return False, graph


@app.route('/check', methods=['POST'])
def check():
    try:
        body = request.get_json(force=True) or {}
        P = int(body.get('P'))
        R = int(body.get('R'))
        alloc = body.get('alloc') or []
        maxd = body.get('maxd') or []
        avail = body.get('avail') or []

        if len(alloc) != P or len(maxd) != P:
            return jsonify({'error': 'Allocation and Max demand must have P rows.'}), 400
        for i in range(P):
            if len(alloc[i]) != R or len(maxd[i]) != R:
                return jsonify({'error': f'Row {i} length mismatch with R.'}), 400
        if len(avail) != R:
            return jsonify({'error': 'Available resources must have length R.'}), 400

        alloc = [[int(x) for x in row] for row in alloc]
        maxd = [[int(x) for x in row] for row in maxd]
        avail = [int(x) for x in avail]

        safe, seq = bankers_algorithm(P, R, alloc, maxd, avail)
        deadlock, graph = detect_deadlock_graph(P, R, alloc, maxd)

        need = [[maxd[i][j] - alloc[i][j] for j in range(R)] for i in range(P)]
        return jsonify({
            'safe': safe,
            'safeSequence': seq,
            'deadlock': deadlock,
            'graph': {'alloc': alloc, 'need': need}
        })
    except Exception as e:
        return jsonify({'error': f'Exception: {str(e)}'}), 500


# ---------- NEW: STATIC ANALYZER API ----------

@app.route("/api/analyze/python", methods=["POST"])
def analyze_py():
    payload = request.get_json(force=True) or {}
    code = payload.get("code", "")
    result = analyze_python_source(code)
    return jsonify(result)


# ---------- NEW: BANKER-ONLY API ----------

@app.route("/api/banker", methods=["POST"])
def banker_api():
    data = request.get_json(force=True) or {}
    allocation = data.get("allocation", [])
    maximum = data.get("maximum", [])
    available = data.get("available", [])

    n = len(maximum)
    if n == 0:
        return jsonify({"safe": True, "sequence": []})
    m = len(available)
    need = [[maximum[i][j] - allocation[i][j] for j in range(m)] for i in range(n)]
    work = available[:]
    finish = [False] * n
    seq = []

    while len(seq) < n:
        progressed = False
        for i in range(n):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(m)):
                for j in range(m):
                    work[j] += allocation[i][j]
                finish[i] = True
                seq.append(i)
                progressed = True
        if not progressed:
            return jsonify({"safe": False, "sequence": []})
    return jsonify({"safe": True, "sequence": seq})


# ---------- NEW: RAG DEADLOCK-ONLY API ----------

@app.route("/api/detect", methods=["POST"])
def detect_api():
    data = request.get_json(force=True) or {}
    allocation = data.get("allocation", [])
    maximum = data.get("maximum", [])

    edges = []
    if allocation:
        n = len(allocation)
        m = len(allocation[0])
        for p in range(n):
            for r in range(m):
                if allocation[p][r] > 0:
                    edges.append((f"R{r}", f"P{p}"))
                if maximum[p][r] - allocation[p][r] > 0:
                    edges.append((f"P{p}", f"R{r}"))

    graph = {}
    for u, v in edges:
        graph.setdefault(u, []).append(v)

    visited = set()
    stack = set()

    def dfs(u):
        if u in stack:
            return True
        if u in visited:
            return False
        visited.add(u)
        stack.add(u)
        for v in graph.get(u, []):
            if dfs(v):
                return True
        stack.remove(u)
        return False

    for node in graph:
        if dfs(node):
            return jsonify({"deadlock": True, "edges": edges})
    return jsonify({"deadlock": False, "edges": edges})


# ---------- NEW: RUNTIME MONITOR APIs ----------

@app.route("/api/monitor/register_thread", methods=["POST"])
def register_thread():
    name = (request.get_json(force=True) or {}).get("name", "thread")
    tid = monitor.register_thread(name)
    return jsonify({"tid": tid})


@app.route("/api/monitor/register_lock", methods=["POST"])
def register_lock():
    lock_name = (request.get_json(force=True) or {}).get("lock_name", "L")
    monitor.register_lock(lock_name)
    return jsonify({"status": "ok"})


@app.route("/api/monitor/events", methods=["GET"])
def monitor_events():
    return jsonify({"events": monitor.dump_events()})


if __name__ == '__main__':
    app.run(port=5000, debug=True)
