// -------- logging --------

function logEvent(msg){
  const log = document.getElementById('eventLog');
  const now = new Date();
  const t = now.toTimeString().slice(0,8);
  log.textContent = `[${t}] ${msg}\n` + log.textContent;
}

// -------- build P×R matrix grids --------

function buildMatricesFromPR(){
  const P = Number(document.getElementById('P').value);
  const R = Number(document.getElementById('R').value);
  if(!P || !R) return;

  const allocGrid = document.getElementById('allocGrid');
  const maxGrid   = document.getElementById('maxGrid');
  const availGrid = document.getElementById('availGrid');

  allocGrid.innerHTML = '';
  maxGrid.innerHTML   = '';
  availGrid.innerHTML = '';

  allocGrid.style.gridTemplateColumns = `repeat(${R}, 46px)`;
  maxGrid.style.gridTemplateColumns   = `repeat(${R}, 46px)`;

  for(let i=0;i<P;i++){
    for(let j=0;j<R;j++){
      const a = document.createElement('input');
      a.type = 'number';
      a.value = '0';
      a.className = 'matrix-cell';
      a.dataset.i = i;
      a.dataset.j = j;
      allocGrid.appendChild(a);

      const m = document.createElement('input');
      m.type = 'number';
      m.value = '0';
      m.className = 'matrix-cell';
      m.dataset.i = i;
      m.dataset.j = j;
      maxGrid.appendChild(m);
    }
  }

  for(let j=0;j<R;j++){
    const av = document.createElement('input');
    av.type = 'number';
    av.value = '0';
    av.className = 'avail-cell';
    av.dataset.j = j;
    availGrid.appendChild(av);
  }

  logEvent(`Built ${P}×${R} matrices.`);
}

// -------- read matrices from grids --------

function readAllocMatrix(P, R){
  const grid = document.getElementById('allocGrid');
  const cells = grid.querySelectorAll('.matrix-cell');
  const mat = Array.from({length:P}, () => Array(R).fill(0));
  cells.forEach(c => {
    const i = Number(c.dataset.i);
    const j = Number(c.dataset.j);
    mat[i][j] = Number(c.value) || 0;
  });
  return mat;
}

function readMaxMatrix(P, R){
  const grid = document.getElementById('maxGrid');
  const cells = grid.querySelectorAll('.matrix-cell');
  const mat = Array.from({length:P}, () => Array(R).fill(0));
  cells.forEach(c => {
    const i = Number(c.dataset.i);
    const j = Number(c.dataset.j);
    mat[i][j] = Number(c.value) || 0;
  });
  return mat;
}

function readAvail(R){
  const grid = document.getElementById('availGrid');
  const cells = grid.querySelectorAll('.avail-cell');
  const arr = Array(R).fill(0);
  cells.forEach(c => {
    const j = Number(c.dataset.j);
    arr[j] = Number(c.value) || 0;
  });
  return arr;
}

// -------- backend interaction --------

async function checkState(){
  const P = Number(document.getElementById('P').value);
  const R = Number(document.getElementById('R').value);
  if(!P || !R){
    logEvent('Error: P and R must be positive integers.');
    return;
  }

  const alloc = readAllocMatrix(P, R);
  const maxd  = readMaxMatrix(P, R);
  const avail = readAvail(R);

  try{
    const resp = await fetch('http://localhost:5000/check', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({P,R,alloc,maxd,avail})
    });
    const data = await resp.json();
    updateResults(data, P, R);
  }catch(e){
    logEvent('Failed to contact backend at http://localhost:5000/check');
    console.error(e);
  }
}

function updateResults(data, P, R){
  const bankerBadge = document.getElementById('bankerBadge');
  const deadBadge   = document.getElementById('deadlockBadge');
  const ragText     = document.getElementById('ragText');

  if(data.error){
    bankerBadge.textContent = 'Error';
    bankerBadge.className = 'pill pill-bad';
    deadBadge.textContent = 'Error';
    deadBadge.className = 'pill pill-bad';
    ragText.textContent = data.error;
    logEvent(`Error: ${data.error}`);
    return;
  }

  if(data.safe){
    bankerBadge.textContent = 'Safe';
    bankerBadge.className = 'pill pill-ok';
    const seq = data.safeSequence.join(' → ') || '—';
    ragText.textContent = `Safe sequence: ${seq}. Deadlock result shown on the right.`;
    logEvent('Banker: system is SAFE.');
  }else{
    bankerBadge.textContent = 'Unsafe';
    bankerBadge.className = 'pill pill-bad';
    ragText.textContent = 'No safe sequence exists. Deadlock result shown on the right.';
    logEvent('Banker: system is UNSAFE.');
  }

  if(data.deadlock){
    deadBadge.textContent = 'Yes';
    deadBadge.className = 'pill pill-bad';
    logEvent('Deadlock detected from RAG edges.');
  }else{
    deadBadge.textContent = 'No';
    deadBadge.className = 'pill pill-ok';
    logEvent('No deadlock detected in RAG.');
  }

  if(data.graph){
    drawGraphFromData(data.graph, P, R);
  }
}

// -------- draw graph from current inputs (Draw Resource Graph button) --------

function drawGraph(){
  const P = Number(document.getElementById('P').value);
  const R = Number(document.getElementById('R').value);
  if(!P || !R) return;

  const alloc = readAllocMatrix(P, R);
  const maxd  = readMaxMatrix(P, R);

  const need = Array.from({length:P}, (_, i) =>
    Array.from({length:R}, (_, j) =>
      (maxd[i] && maxd[i][j] ? maxd[i][j] : 0) -
      (alloc[i] && alloc[i][j] ? alloc[i][j] : 0)
    )
  );

  const graph = {alloc, need};
  drawGraphFromData(graph, P, R);
}

// -------- SVG RAG drawing --------

function drawGraphFromData(graph, P, R){
  const wrap = document.getElementById('graphWrap');
  wrap.innerHTML = '';

  const width = wrap.clientWidth || 500;
  const height = wrap.clientHeight || 360;
  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS,'svg');
  svg.setAttribute('viewBox',`0 0 ${width} ${height}`);

  const defs = document.createElementNS(svgNS,'defs');
  defs.innerHTML =
    `<marker id="arrowAlloc" viewBox="0 0 10 10" refX="8" refY="5"
              markerWidth="6" markerHeight="6" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#22c55e" />
     </marker>
     <marker id="arrowNeed" viewBox="0 0 10 10" refX="8" refY="5"
              markerWidth="6" markerHeight="6" orient="auto">
        <path d="M 0 0 L 10 5 L 0 10 z" fill="#fb7185" />
     </marker>`;
  svg.appendChild(defs);

  const leftX = 90;
  const rightX = width - 120;
  const pGap = Math.max(60, (height - 60)/Math.max(1,P));
  const rGap = Math.max(60, (height - 60)/Math.max(1,R));

  const procCoords = [];
  for(let i=0;i<P;i++){
    const cx = leftX;
    const cy = 40 + i*pGap;
    procCoords.push([cx,cy]);

    const g = document.createElementNS(svgNS,'g');
    const rect = document.createElementNS(svgNS,'rect');
    rect.setAttribute('x',cx-32);
    rect.setAttribute('y',cy-18);
    rect.setAttribute('width',64);
    rect.setAttribute('height',36);
    rect.setAttribute('rx',10);
    rect.setAttribute('class','nodeProc');
    g.appendChild(rect);

    const t = document.createElementNS(svgNS,'text');
    t.setAttribute('x',cx);
    t.setAttribute('y',cy+4);
    t.setAttribute('text-anchor','middle');
    t.setAttribute('class','textNode');
    t.textContent = `P${i}`;
    g.appendChild(t);

    svg.appendChild(g);
  }

  const resCoords = [];
  for(let j=0;j<R;j++){
    const cx = rightX;
    const cy = 40 + j*rGap;
    resCoords.push([cx,cy]);

    const g = document.createElementNS(svgNS,'g');
    const circle = document.createElementNS(svgNS,'circle');
    circle.setAttribute('cx',cx);
    circle.setAttribute('cy',cy);
    circle.setAttribute('r',22);
    circle.setAttribute('class','nodeRes');
    g.appendChild(circle);

    const t = document.createElementNS(svgNS,'text');
    t.setAttribute('x',cx);
    t.setAttribute('y',cy+4);
    t.setAttribute('text-anchor','middle');
    t.setAttribute('class','textNode');
    t.textContent = `R${j}`;
    g.appendChild(t);

    svg.appendChild(g);
  }

  const alloc = graph.alloc || [];
  const need = graph.need || [];

  for(let p=0;p<P;p++){
    for(let r=0;r<R;r++){
      const [px,py] = procCoords[p];
      const [rx,ry] = resCoords[r];

      if(alloc[p] && alloc[p][r] > 0){
        const line = document.createElementNS(svgNS,'line');
        line.setAttribute('x1',rx-22);
        line.setAttribute('y1',ry);
        line.setAttribute('x2',px+32);
        line.setAttribute('y2',py);
        line.setAttribute('class','edgeAlloc');
        svg.appendChild(line);
      }

      if(need[p] && need[p][r] > 0){
        const line = document.createElementNS(svgNS,'line');
        line.setAttribute('x1',px+32);
        line.setAttribute('y1',py);
        line.setAttribute('x2',rx-22);
        line.setAttribute('y2',ry);
        line.setAttribute('class','edgeNeed');
        svg.appendChild(line);
      }
    }
  }

  wrap.appendChild(svg);
}

// -------- load sample --------

function fillExample(){
  document.getElementById('P').value = 3;
  document.getElementById('R').value = 3;
  buildMatricesFromPR();

  const alloc = [
    [0,1,0],
    [2,0,0],
    [3,0,3]
  ];
  const maxd = [
    [7,5,3],
    [3,2,2],
    [9,0,4]
  ];
  const avail = [2,3,0];

  const aCells = document.querySelectorAll('#allocGrid .matrix-cell');
  const mCells = document.querySelectorAll('#maxGrid .matrix-cell');
  aCells.forEach(c => {
    const i = Number(c.dataset.i), j = Number(c.dataset.j);
    c.value = alloc[i][j];
  });
  mCells.forEach(c => {
    const i = Number(c.dataset.i), j = Number(c.dataset.j);
    c.value = maxd[i][j];
  });
  const avCells = document.querySelectorAll('#availGrid .avail-cell');
  avCells.forEach(c => {
    const j = Number(c.dataset.j);
    c.value = avail[j];
  });

  logEvent('Loaded sample matrices.');
  drawGraph();
}

// initial wiring
window.addEventListener('DOMContentLoaded', () => {
  document.getElementById('P').addEventListener('change', buildMatricesFromPR);
  document.getElementById('R').addEventListener('change', buildMatricesFromPR);
  buildMatricesFromPR();
  drawGraph();
});