# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
app = Flask(__name__)
CORS(app)

def bankers_algorithm(P, R, alloc, maxd, avail):
    # convert to mutable lists and validate shapes
    work = avail[:]  # copy
    finish = [False]*P

    need = [[0]*R for _ in range(P)]
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
                    # simulate running the process
                    for j in range(R):
                        work[j] += alloc[i][j]
                    finish[i] = True
                    safe_sequence.append(f"P{i}")
                    progressed = True
        if not progressed:
            break

    safe = all(finish)
    return safe, safe_sequence if safe else []

# build resource-allocation graph and detect cycle (directed cycle in bipartite graph)
def detect_deadlock_graph(P, R, alloc, maxd):
    total = P + R
    # adjacency list for directed graph
    graph = [[] for _ in range(total)]
    # build edges:
    # if alloc[p][r] > 0: resource node (P+r) -> process node p (allocation)
    # if need[p][r] > 0: process node p -> resource node (P+r) (request)
    need = [[maxd[i][j] - alloc[i][j] for j in range(R)] for i in range(P)]

    for p in range(P):
        for r in range(R):
            pNode = p
            rNode = P + r
            if alloc[p][r] > 0:
                graph[rNode].append(pNode)
            if need[p][r] > 0:
                graph[pNode].append(rNode)

    # DFS for cycle detection in directed graph
    color = [0]*total  # 0 = unvisited, 1 = visiting, 2 = visited
    def dfs(u):
        color[u] = 1
        for v in graph[u]:
            if color[v] == 1:
                return True
            if color[v] == 0:
                if dfs(v):
                    return True
        color[u] = 2
        return False

    for node in range(total):
        if color[node] == 0:
            if dfs(node):
                return True, graph
    return False, graph

@app.route('/check', methods=['POST'])
def check():
    try:
        body = request.get_json(force=True)
        P = int(body.get('P'))
        R = int(body.get('R'))
        alloc = body.get('alloc') or []
        maxd = body.get('maxd') or []
        avail = body.get('avail') or []

        # basic validations and shape fixes:
        if len(alloc) != P or len(maxd) != P:
            return jsonify({'error':'Allocation and Max demand must have P rows.'}), 400
        for i in range(P):
            if len(alloc[i]) != R or len(maxd[i]) != R:
                return jsonify({'error':f'Row {i} length mismatch with R.'}), 400
        if len(avail) != R:
            return jsonify({'error':'Available resources must have length R.'}), 400

        # ensure ints
        alloc = [[int(x) for x in row] for row in alloc]
        maxd = [[int(x) for x in row] for row in maxd]
        avail = [int(x) for x in avail]

        safe, seq = bankers_algorithm(P,R,alloc,maxd,avail)
        deadlock, graph = detect_deadlock_graph(P,R,alloc,maxd)

        # return minimal graph data for drawing (alloc and need)
        need = [[maxd[i][j] - alloc[i][j] for j in range(R)] for i in range(P)]
        return jsonify({'safe':safe,'safeSequence':seq,'deadlock':deadlock,'graph':{'alloc':alloc,'need':need}})
    except Exception as e:
        return jsonify({'error':f'Exception: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(port=5000, debug=True)