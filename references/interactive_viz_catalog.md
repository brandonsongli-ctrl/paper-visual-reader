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

## Integration Checklist

When generating a digest, the agent should:

1. After extracting all results, scan for visualization triggers (see table in SKILL.md)
2. For each triggered result, select the appropriate template from this catalog
3. Customize the template with the paper's specific payoffs, parameters, notation
4. Use examples from the paper as preset buttons
5. Embed the `<div class="interactive-viz">` + `<script>` after the result card
6. Include the viz CSS classes and `toggleFullscreen()` function once in the document head
7. Test mentally that the visualization correctly represents the mathematical content
