# Interactive Visualization Catalog

Reusable code templates for inline Canvas-based interactive visualizations in paper digests.

## General Utilities

```javascript
// Fullscreen toggle (include once in digest)
function toggleFullscreen(id) {
  const el = document.getElementById(id);
  el.classList.toggle('fullscreen');
  // Re-trigger resize
  window.dispatchEvent(new Event('resize'));
}

// Get theme-aware colors
function getThemeColors() {
  const dark = document.documentElement.dataset.theme === 'dark';
  return {
    bg: dark ? '#1a1c2a' : '#ffffff',
    axis: dark ? '#9ca3af' : '#374151',
    grid: dark ? '#2a2d3e' : '#e5e7eb',
    text: dark ? '#e5e7eb' : '#1a1d23',
    textSec: dark ? '#9ca3af' : '#6b7280',
    surface: dark ? '#1e2030' : '#f7f8fa',
  };
}

// Color palette (colorblind-friendly)
const COLORS = ['#2563eb','#dc2626','#059669','#d97706','#7c3aed','#0891b2'];
```

---

## Type 1: EU Lines + Belief Partition (Two-State)

**Trigger**: Optimal action as function of belief, threshold beliefs, N(a) sets, binary state.

```javascript
(function() {
  const canvas = document.getElementById('canvas-{ID}');
  const ctx = canvas.getContext('2d');

  // Data: actions with payoffs u(a|L) and u(a|H)
  let actions = [
    { name: 'a₀', uL: 1, uH: 0, color: COLORS[0] },
    { name: 'a₁', uL: 0, uH: 1, color: COLORS[1] },
  ];

  let hoverP = null; // current hover belief p = Pr(H)
  const pad = { top: 30, right: 30, bottom: 60, left: 50 };

  function eu(a, p) { return (1 - p) * a.uL + p * a.uH; }

  function optimalAction(p) {
    let best = 0, bestEU = eu(actions[0], p);
    for (let i = 1; i < actions.length; i++) {
      const v = eu(actions[i], p);
      if (v > bestEU) { bestEU = v; best = i; }
    }
    return best;
  }

  // Find indifference points between adjacent optimal actions
  function indifferencePoints() {
    const pts = [];
    for (let i = 0; i < actions.length; i++)
      for (let j = i + 1; j < actions.length; j++) {
        // (1-p)(uiL - ujL) + p(uiH - ujH) = 0
        const dL = actions[i].uL - actions[j].uL;
        const dH = actions[i].uH - actions[j].uH;
        if (Math.abs(dL - dH) > 1e-12) {
          const p = dL / (dL - dH);
          if (p > 0 && p < 1) pts.push({ p, i, j });
        }
      }
    return pts.sort((a, b) => a.p - b.p);
  }

  function draw() {
    const W = canvas.width, H = canvas.height;
    const tc = getThemeColors();
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = tc.bg;
    ctx.fillRect(0, 0, W, H);

    const plotW = W - pad.left - pad.right;
    const plotH = H - pad.top - pad.bottom;

    // Compute EU range
    let minEU = Infinity, maxEU = -Infinity;
    for (const a of actions) {
      for (const p of [0, 1]) {
        const v = eu(a, p);
        minEU = Math.min(minEU, v);
        maxEU = Math.max(maxEU, v);
      }
    }
    const euRange = maxEU - minEU || 1;
    minEU -= euRange * 0.1;
    maxEU += euRange * 0.1;

    function toX(p) { return pad.left + p * plotW; }
    function toY(v) { return pad.top + (1 - (v - minEU) / (maxEU - minEU)) * plotH; }

    // Grid
    ctx.strokeStyle = tc.grid; ctx.lineWidth = 0.5;
    for (let i = 0; i <= 4; i++) {
      const y = pad.top + (i / 4) * plotH;
      ctx.beginPath(); ctx.moveTo(pad.left, y); ctx.lineTo(W - pad.right, y); ctx.stroke();
    }

    // Axes
    ctx.strokeStyle = tc.axis; ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(pad.left, pad.top); ctx.lineTo(pad.left, H - pad.bottom);
    ctx.lineTo(W - pad.right, H - pad.bottom); ctx.stroke();

    // Axis labels
    ctx.fillStyle = tc.text; ctx.font = '12px Inter, sans-serif'; ctx.textAlign = 'center';
    ctx.fillText('p = Pr(H)', W / 2, H - 8);
    ctx.save(); ctx.translate(14, H / 2); ctx.rotate(-Math.PI / 2);
    ctx.fillText('Expected Utility', 0, 0); ctx.restore();

    // N(a) bands on x-axis
    const bandY = H - pad.bottom + 5;
    const bandH = 15;
    const indPts = indifferencePoints();
    // ... (compute and draw colored bands)

    // EU lines
    for (const a of actions) {
      ctx.strokeStyle = a.color; ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(toX(0), toY(eu(a, 0)));
      ctx.lineTo(toX(1), toY(eu(a, 1)));
      ctx.stroke();
      // Label
      ctx.fillStyle = a.color; ctx.font = 'bold 11px Inter';
      ctx.textAlign = 'left';
      ctx.fillText(a.name, toX(1) + 4, toY(eu(a, 1)));
    }

    // Upper envelope (bold)
    ctx.strokeStyle = tc.text; ctx.lineWidth = 3;
    ctx.beginPath();
    for (let px = 0; px <= 200; px++) {
      const p = px / 200;
      const maxV = Math.max(...actions.map(a => eu(a, p)));
      const x = toX(p), y = toY(maxV);
      px === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Hover line
    if (hoverP !== null) {
      ctx.setLineDash([4, 4]); ctx.strokeStyle = tc.textSec; ctx.lineWidth = 1;
      ctx.beginPath(); ctx.moveTo(toX(hoverP), pad.top); ctx.lineTo(toX(hoverP), H - pad.bottom); ctx.stroke();
      ctx.setLineDash([]);
      // Dots on each line
      for (const a of actions) {
        const v = eu(a, hoverP);
        ctx.fillStyle = a.color;
        ctx.beginPath(); ctx.arc(toX(hoverP), toY(v), 5, 0, Math.PI * 2); ctx.fill();
      }
    }
  }

  canvas.addEventListener('mousemove', e => {
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    hoverP = Math.max(0, Math.min(1, (x - pad.left) / (canvas.width - pad.left - pad.right)));
    draw();
  });
  canvas.addEventListener('mouseleave', () => { hoverP = null; draw(); });

  draw();
})();
```

---

## Type 2: Concavification Diagram

**Trigger**: Concave closure, value function V̂(μ), persuasion value.

Shows v̂(μ) = v(â(μ)) as a piecewise linear function and its concave envelope V̂(μ).

Key features:
- Plot v̂(μ) in blue (piecewise linear, typically non-concave)
- Plot V̂(μ) in red (concave envelope, the "roof")
- Shade the gap V̂ - v̂ (persuasion surplus)
- Mark the prior μ₀ with a vertical line
- Show the optimal splitting: posteriors p, q with Bayes plausibility λp + (1-λ)q = μ₀
- Draggable prior μ₀

---

## Type 3: Simplex Heatmap (Three-State)

**Trigger**: Optimal action regions on 2-simplex.

Renders an equilateral triangle (the 2-simplex) with colored regions.

Key features:
- Pixel-level rasterization: for each pixel, compute barycentric coordinates, evaluate EU for each action, color by optimal action
- Boundary lines between regions (indifference hyperplanes)
- Hover: show belief triple and all EU values
- Draggable payoff points (via control panel)

---

## Type 4: Payoff Space + Supporting Hyperplane

**Trigger**: Payoff vectors φ(a), normal cones, supporting hyperplanes.

Two-panel layout:
- Left: EU lines (Type 1)
- Right: R² payoff space with φ(a) points, Φ shaded, supporting hyperplane rotating with hover

---

## Type 5: Comparative Statics Slider

**Trigger**: Result states "increasing/decreasing in parameter."

Shows how a curve or value changes as a parameter varies.

Key features:
- Horizontal slider for the parameter
- Plot updates in real-time as slider moves
- Mark critical values (discontinuities, phase transitions)
- Show before/after overlay

---

## Type 6: Posterior Distribution / Bayes Plausibility

**Trigger**: Signal structures, distribution of posteriors, information design.

Shows:
- A distribution of posteriors on [0,1] (histogram or density)
- Bayes plausibility constraint: E[μ] = μ₀ (marked)
- The action threshold: posteriors above c induce action 1
- Draggable signal parameters

---

## Type 7: Threshold Diagram

**Trigger**: Cutoff rules, threshold beliefs, binary decisions.

Simple but effective:
- Number line [0,1] representing beliefs
- Colored regions: below threshold → action 0, above → action 1
- The threshold c marked with a triangle
- Slider to change parameters, threshold updates

---

## Type 8: Playground (Click-to-Draw + Real-Time Computation)

**Trigger**: Theory papers where readers benefit from exploring custom functions (e.g., custom value functions, custom distributions, custom cost curves) and seeing real-time mathematical transformations (e.g., concavification, convex hull, optimal mechanism).

A full-featured interactive sandbox at the end of the digest.

### Structure

```html
<div class="interactive-viz playground-viz" id="viz-playground">
  <div class="viz-header">
    <span class="viz-badge">Playground</span>
    <span class="viz-title">{Description, e.g. "Draw your own v-hat and see the concavification"}</span>
    <button class="viz-fullscreen-btn" onclick="toggleFullscreen('viz-playground')">&#x26F6;</button>
  </div>
  <div class="viz-body">
    <canvas id="canvas-playground" width="800" height="450"></canvas>
  </div>
  <div class="viz-controls">
    <button class="active" onclick="loadPreset(0)">Paper Example 1</button>
    <button onclick="loadPreset(1)">Paper Example 2</button>
    <button onclick="clearCanvas()">Clear &amp; Draw</button>
    <label>Parameter: <input type="range" min="0" max="100" value="50" oninput="updateParam(this.value)"></label>
  </div>
  <div class="viz-caption"><p>Click on the canvas to place control points. The transformation updates in real time.</p></div>
</div>
```

### Key Features

1. **Click-to-draw**: Users click on the canvas to place control points defining a custom function. Points are interpolated (linear or cubic spline) to form a curve.
2. **Real-time transformation**: As soon as the user draws, the mathematical transformation (concavification, convex hull, optimal mechanism, etc.) is computed and rendered as an overlay curve.
3. **Preset buttons**: 2-3 presets that load specific functions from the paper's examples. First preset loads by default so the canvas is never empty.
4. **Parameter sliders**: Adjust model parameters (e.g., prior, cost, discount factor) that affect the transformation but not the drawn function.
5. **Clear and redraw**: A button to clear user-drawn points and start fresh.

### Implementation Pattern

```javascript
(function() {
  const canvas = document.getElementById('canvas-playground');
  const ctx = canvas.getContext('2d');
  let userPoints = [];  // [{x, y}, ...] user-clicked control points
  let paramValue = 0.5;

  // Presets: arrays of {x, y} matching paper examples
  const presets = [
    [ {x:0, y:0.2}, {x:0.3, y:0.8}, {x:0.6, y:0.3}, {x:1, y:0.9} ],
    [ {x:0, y:0.5}, {x:0.5, y:0.1}, {x:1, y:0.7} ],
  ];

  function loadPreset(i) {
    userPoints = [...presets[i]];
    draw();
  }

  function clearCanvas() {
    userPoints = [];
    draw();
  }

  function updateParam(v) {
    paramValue = v / 100;
    draw();
  }

  // Compute transformation (paper-specific, e.g., concavification)
  function computeTransformation(pts) {
    // ... paper-specific math
    return transformedPts;
  }

  function draw() {
    // DPR-aware sizing
    const dpr = window.devicePixelRatio || 1;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * dpr;
    canvas.height = rect.height * dpr;
    ctx.scale(dpr, dpr);

    const W = rect.width, H = rect.height;
    const tc = getThemeColors();
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = tc.bg;
    ctx.fillRect(0, 0, W, H);

    // Draw user function
    if (userPoints.length >= 2) {
      ctx.strokeStyle = COLORS[0]; ctx.lineWidth = 2;
      ctx.beginPath();
      userPoints.sort((a, b) => a.x - b.x);
      for (let i = 0; i < userPoints.length; i++) {
        const px = userPoints[i].x * W, py = (1 - userPoints[i].y) * H;
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      }
      ctx.stroke();

      // Draw transformation overlay
      const transformed = computeTransformation(userPoints);
      ctx.strokeStyle = COLORS[1]; ctx.lineWidth = 2.5;
      ctx.setLineDash([6, 3]);
      ctx.beginPath();
      for (let i = 0; i < transformed.length; i++) {
        const px = transformed[i].x * W, py = (1 - transformed[i].y) * H;
        i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
      }
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // Draw control points with shadow
    for (const pt of userPoints) {
      const px = pt.x * W, py = (1 - pt.y) * H;
      ctx.save();
      ctx.shadowColor = 'rgba(0,0,0,0.25)';
      ctx.shadowBlur = 4;
      ctx.shadowOffsetY = 1;
      ctx.fillStyle = COLORS[0];
      ctx.beginPath(); ctx.arc(px, py, 5, 0, Math.PI * 2); ctx.fill();
      ctx.restore();
    }
  }

  canvas.addEventListener('click', e => {
    const rect = canvas.getBoundingClientRect();
    const x = (e.clientX - rect.left) / rect.width;
    const y = 1 - (e.clientY - rect.top) / rect.height;
    userPoints.push({x, y});
    draw();
  });

  // Load first preset by default
  loadPreset(0);
})();
```

### CSS Addition

```css
.playground-viz { border: 2px solid var(--accent-blue-border); }
.playground-viz .viz-header { background: linear-gradient(135deg, var(--accent-blue), var(--accent-blue-border)); }
```

---

## Enhanced Canvas Rendering (v5)

All canvas-based visualizations SHOULD incorporate these rendering enhancements for a polished, modern appearance.

### DPR-Aware Rendering

All canvases must scale for high-DPI displays:

```javascript
function setupCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  const ctx = canvas.getContext('2d');
  ctx.scale(dpr, dpr);
  return { ctx, W: rect.width, H: rect.height };
}
```

### Gradient Fills for Regions

Use gradient fills (not flat alpha) for shaded regions between curves:

```javascript
function fillRegionGradient(ctx, topY, bottomY, x0, x1, color, W) {
  const grad = ctx.createLinearGradient(0, topY, 0, bottomY);
  grad.addColorStop(0, color + '40');  // 25% alpha at top
  grad.addColorStop(1, color + '08');  // 3% alpha at bottom
  ctx.fillStyle = grad;
  // ... fill path between curves
}
```

### Dot Rendering with Shadows

Data points and control points should have subtle drop shadows:

```javascript
function drawDot(ctx, x, y, radius, color) {
  ctx.save();
  ctx.shadowColor = 'rgba(0,0,0,0.25)';
  ctx.shadowBlur = 4;
  ctx.shadowOffsetX = 0;
  ctx.shadowOffsetY = 1;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(x, y, radius, 0, Math.PI * 2);
  ctx.fill();
  ctx.restore();
}
```

### Canvas Hover Tooltips

Show a floating `<div>` with coordinate values on mousemove:

```javascript
// Create tooltip div (once per viz)
const tooltip = document.createElement('div');
tooltip.className = 'canvas-tooltip';
tooltip.style.cssText = 'position:absolute;display:none;pointer-events:none;' +
  'background:var(--card-bg);border:1px solid var(--card-border);border-radius:6px;' +
  'padding:6px 10px;font-family:Inter,sans-serif;font-size:0.75rem;' +
  'color:var(--text-body);box-shadow:0 2px 8px rgba(0,0,0,0.12);z-index:100;white-space:nowrap;';
canvas.parentElement.style.position = 'relative';
canvas.parentElement.appendChild(tooltip);

canvas.addEventListener('mousemove', e => {
  const rect = canvas.getBoundingClientRect();
  const mx = e.clientX - rect.left, my = e.clientY - rect.top;
  // Convert to data coordinates
  const dataX = /* ... */, dataY = /* ... */;
  tooltip.style.display = 'block';
  tooltip.style.left = (mx + 12) + 'px';
  tooltip.style.top = (my - 8) + 'px';
  tooltip.innerHTML = `<b>x</b>: ${dataX.toFixed(3)}, <b>y</b>: ${dataY.toFixed(3)}`;
});

canvas.addEventListener('mouseleave', () => {
  tooltip.style.display = 'none';
});
```

---

## Integration Checklist

When generating a digest, the agent should:

1. After extracting all results, scan for visualization triggers (see table in SKILL.md)
2. For each triggered result, select the appropriate template from this catalog
3. Customize the template with the paper's specific payoffs, parameters, notation
4. Use examples from the paper as preset buttons
5. Embed the `<div class="interactive-viz">` + `<script>` after the result card
6. Include the viz CSS classes and `toggleFullscreen()` function once in the document head
7. Test mentally that the visualization correctly represents the mathematical content
8. For theory papers, include a Playground section at the end of the digest (Type 8)
9. All canvases use DPR-aware rendering via `setupCanvas()` (v5)
10. Region fills use gradient (not flat alpha), dots have `shadowBlur`, hover shows coordinate tooltip (v5)
