/**
 * MAT-VLAB Mathematical Formula Rendering Controller
 * Powered by MathJax 3 (SVG Engine) with Zero-Raw-LaTeX Instant Fallback
 * Ensures publication-grade mathematical typography across all pages & dynamic content.
 */

(function () {
  'use strict';

  /**
   * Pure JavaScript LaTeX-to-HTML parser
   * Converts TeX mathematical notation into semantic HTML/CSS elements.
   * Guarantees that raw LaTeX ($$, $, \\frac, \\sqrt, etc.) is NEVER shown to students.
   */
  function extractBraced(s, startIndex) {
    if (s[startIndex] !== '{') return null;
    let depth = 0;
    for (let i = startIndex; i < s.length; i++) {
      if (s[i] === '{') depth++;
      else if (s[i] === '}') {
        depth--;
        if (depth === 0) {
          return { content: s.substring(startIndex + 1, i), endIndex: i };
        }
      }
    }
    return null;
  }

  function parseTexToHtml(tex) {
    if (!tex) return '';
    const str = tex.trim();

    function parseExpr(expr) {
      let out = '';
      let i = 0;
      while (i < expr.length) {
        // 1. \frac{num}{den}
        if (expr.substring(i, i + 6) === '\\frac{') {
          const numRes = extractBraced(expr, i + 5);
          if (numRes) {
            const nextIdx = numRes.endIndex + 1;
            if (expr[nextIdx] === '{') {
              const denRes = extractBraced(expr, nextIdx);
              if (denRes) {
                const numHtml = parseExpr(numRes.content);
                const denHtml = parseExpr(denRes.content);
                out += `<span class="math-fallback-frac"><span class="math-fallback-num">${numHtml}</span><span class="math-fallback-den">${denHtml}</span></span>`;
                i = denRes.endIndex + 1;
                continue;
              }
            }
          }
        }

        // 2. \sqrt{radicand}
        if (expr.substring(i, i + 6) === '\\sqrt{') {
          const radRes = extractBraced(expr, i + 5);
          if (radRes) {
            const radHtml = parseExpr(radRes.content);
            out += `<span class="math-fallback-sqrt"><span class="math-fallback-radical">&radic;</span><span class="math-fallback-radicand">${radHtml}</span></span>`;
            i = radRes.endIndex + 1;
            continue;
          }
        }

        // 3. \text{...}
        if (expr.substring(i, i + 6) === '\\text{') {
          const textRes = extractBraced(expr, i + 5);
          if (textRes) {
            out += `<span class="math-sym">${textRes.content}</span>`;
            i = textRes.endIndex + 1;
            continue;
          }
        }

        // 4. \mathbf{...}
        if (expr.substring(i, i + 8) === '\\mathbf{') {
          const bfRes = extractBraced(expr, i + 7);
          if (bfRes) {
            out += `<strong>${parseExpr(bfRes.content)}</strong>`;
            i = bfRes.endIndex + 1;
            continue;
          }
        }

        // 5. Greek letters & symbols
        if (expr[i] === '\\') {
          const slice = expr.substring(i);
          const symbolMap = [
            ['\\pi', '&pi;'],
            ['\\sigma', '&sigma;'],
            ['\\epsilon', '&epsilon;'],
            ['\\Delta', '&Delta;'],
            ['\\alpha', '&alpha;'],
            ['\\beta', '&beta;'],
            ['\\gamma', '&gamma;'],
            ['\\mu', '&mu;'],
            ['\\cdot', '&middot;'],
            ['\\times', '&times;'],
            ['\\approx', '&asymp;'],
            ['\\quad', '&nbsp;&nbsp;'],
            ['\\qquad', '&nbsp;&nbsp;&nbsp;&nbsp;'],
            ['\\left(', '('],
            ['\\right)', ')'],
            ['\\left[', '['],
            ['\\right]', ']'],
            ['\\left\\{', '{'],
            ['\\right\\}', '}'],
            ['\\%', '%'],
            ['\\le', '&le;'],
            ['\\ge', '&ge;'],
            ['\\max', 'max']
          ];
          let matched = false;
          for (const [texSym, htmlSym] of symbolMap) {
            if (slice.startsWith(texSym)) {
              out += htmlSym;
              i += texSym.length;
              matched = true;
              break;
            }
          }
          if (matched) continue;
        }

        // 6. Superscript ^{...} or ^x
        if (expr[i] === '^') {
          if (expr[i + 1] === '{') {
            const supRes = extractBraced(expr, i + 1);
            if (supRes) {
              out += `<sup>${parseExpr(supRes.content)}</sup>`;
              i = supRes.endIndex + 1;
              continue;
            }
          } else if (i + 1 < expr.length && /[a-zA-Z0-9]/.test(expr[i + 1])) {
            out += `<sup>${expr[i + 1]}</sup>`;
            i += 2;
            continue;
          }
        }

        // 7. Subscript _{...} or _x
        if (expr[i] === '_') {
          if (expr[i + 1] === '{') {
            const subRes = extractBraced(expr, i + 1);
            if (subRes) {
              out += `<sub>${parseExpr(subRes.content)}</sub>`;
              i = subRes.endIndex + 1;
              continue;
            }
          } else if (i + 1 < expr.length && /[a-zA-Z0-9]/.test(expr[i + 1])) {
            out += `<sub>${expr[i + 1]}</sub>`;
            i += 2;
            continue;
          }
        }

        // 8. Variables & units
        const char = expr[i];
        if (/[a-zA-Z]/.test(char)) {
          let word = '';
          let j = i;
          while (j < expr.length && /[a-zA-Z]/.test(expr[j])) {
            word += expr[j];
            j++;
          }
          if (['HBW', 'HRA', 'HRB', 'HRC', 'HRD', 'HRF', 'UTS', 'MPa', 'GPa', 'kN', 'kgf', 'mm', 'EL', 'RA'].includes(word)) {
            out += `<span class="math-sym">${word}</span>`;
            i = j;
            continue;
          } else if (word.length === 1) {
            out += `<span class="math-var">${word}</span>`;
            i = j;
            continue;
          } else {
            out += `<span class="math-sym">${word}</span>`;
            i = j;
            continue;
          }
        }

        // Default character
        out += char;
        i++;
      }
      return out;
    }

    return parseExpr(str);
  }

  /**
   * Scans container for unrendered LaTeX text and converts it into styled HTML.
   */
  function applyCleanFallbackMath(root) {
    const container = root || document.body;
    if (!container) return;

    const walker = document.createTreeWalker(
      container,
      NodeFilter.SHOW_TEXT,
      {
        acceptNode: function (node) {
          const parent = node.parentElement;
          if (!parent) return NodeFilter.FILTER_REJECT;
          const tag = parent.tagName.toLowerCase();
          if (tag === 'script' || tag === 'style' || tag === 'textarea' || tag === 'mjx-container') {
            return NodeFilter.FILTER_REJECT;
          }
          if (parent.closest('mjx-container') || parent.classList.contains('mat-fallback-rendered')) {
            return NodeFilter.FILTER_REJECT;
          }
          const val = node.nodeValue || '';
          if (val.includes('$') || val.includes('\\frac') || val.includes('\\sqrt') || val.includes('\\[') || val.includes('\\(')) {
            return NodeFilter.FILTER_ACCEPT;
          }
          return NodeFilter.FILTER_SKIP;
        }
      }
    );

    const textNodes = [];
    let currentNode;
    while ((currentNode = walker.nextNode())) {
      textNodes.push(currentNode);
    }

    textNodes.forEach(node => {
      const text = node.nodeValue;
      let hasMath = false;
      let newHtml = text;

      // Display math: $$...$$ or \[...\]
      if (newHtml.includes('$$')) {
        newHtml = newHtml.replace(/\$\$(.+?)\$\$/gs, (match, formula) => {
          hasMath = true;
          return `<div class="math-display mat-fallback-rendered mat-fallback-math">${parseTexToHtml(formula)}</div>`;
        });
      }
      if (newHtml.includes('\\[') && newHtml.includes('\\]')) {
        newHtml = newHtml.replace(/\\\[(.+?)\\\]/gs, (match, formula) => {
          hasMath = true;
          return `<div class="math-display mat-fallback-rendered mat-fallback-math">${parseTexToHtml(formula)}</div>`;
        });
      }

      // Inline math: $...$ or \(...\)
      if (newHtml.includes('$')) {
        newHtml = newHtml.replace(/\$([^$]+?)\$/g, (match, formula) => {
          hasMath = true;
          return `<span class="math-inline mat-fallback-rendered mat-fallback-math">${parseTexToHtml(formula)}</span>`;
        });
      }
      if (newHtml.includes('\\(') && newHtml.includes('\\)')) {
        newHtml = newHtml.replace(/\\\((.+?)\\\)/g, (match, formula) => {
          hasMath = true;
          return `<span class="math-inline mat-fallback-rendered mat-fallback-math">${parseTexToHtml(formula)}</span>`;
        });
      }

      // Standalone LaTeX without delimiters
      if (newHtml.includes('\\frac') || newHtml.includes('\\sqrt')) {
        hasMath = true;
        newHtml = `<span class="math-inline mat-fallback-rendered mat-fallback-math">${parseTexToHtml(newHtml)}</span>`;
      }

      if (hasMath && node.parentNode) {
        const span = document.createElement('span');
        span.innerHTML = newHtml;
        node.parentNode.replaceChild(span, node);
      }
    });
  }

  /**
   * Safe global helper to typeset mathematical equations using MathJax 3.
   * Falls back seamlessly to instant pure HTML math if MathJax is unavailable.
   */
  function renderMath(elements) {
    if (window.MathJax && typeof MathJax.typesetPromise === 'function') {
      try {
        const target = elements ? (Array.isArray(elements) ? elements : [elements]) : null;
        if (target && typeof MathJax.typesetClear === 'function') {
          try {
            MathJax.typesetClear(target);
          } catch (clearErr) {}
        }
        return MathJax.typesetPromise(target ? target : undefined)
          .then(() => {
            // Apply fallback on any missed nodes
            applyCleanFallbackMath(elements);
          })
          .catch(err => {
            console.warn('[MAT-VLAB MathJax] typesetPromise error, applying fallback:', err);
            applyCleanFallbackMath(elements);
          });
      } catch (err) {
        console.warn('[MAT-VLAB MathJax] Error invoking typesetPromise, applying fallback:', err);
        applyCleanFallbackMath(elements);
        return Promise.resolve();
      }
    } else if (window.MathJax && window.MathJax.startup && window.MathJax.startup.promise) {
      return window.MathJax.startup.promise
        .then(() => renderMath(elements))
        .catch(() => applyCleanFallbackMath(elements));
    } else {
      // MathJax not ready yet: execute clean fallback immediately to avoid raw code flash
      applyCleanFallbackMath(elements);
      return Promise.resolve();
    }
  }

  // Expose globally
  window.renderMath = renderMath;
  window.triggerMathRender = function (container) {
    return renderMath(container);
  };
  window.applyCleanFallbackMath = applyCleanFallbackMath;
  window.parseTexToHtml = parseTexToHtml;

  // Event Listeners for Dynamic UI components (Tabs, Collapses, Modals, Hash links)
  document.addEventListener('shown.bs.tab', function (event) {
    const targetId = event.target.getAttribute('data-bs-target') || event.target.getAttribute('href');
    if (targetId) {
      const pane = document.querySelector(targetId);
      renderMath(pane || document.body);
    } else {
      renderMath();
    }
  });

  document.addEventListener('shown.bs.collapse', function (event) {
    renderMath(event.target);
  });

  document.addEventListener('shown.bs.modal', function (event) {
    renderMath(event.target);
  });

  window.addEventListener('hashchange', function () {
    renderMath();
  });

  // Dynamic DOM MutationObserver
  let scheduledNodes = new Set();
  let rafId = null;

  function processScheduledNodes() {
    scheduledNodes.forEach(node => {
      if (node && node.isConnected) {
        renderMath(node);
      }
    });
    scheduledNodes.clear();
    rafId = null;
  }

  function initMutationObserver() {
    if (typeof MutationObserver === 'undefined') return;

    const observer = new MutationObserver(mutations => {
      let shouldProcess = false;
      mutations.forEach(mutation => {
        if (mutation.type === 'childList') {
          mutation.addedNodes.forEach(node => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              const tag = node.tagName.toLowerCase();
              if (tag !== 'mjx-container' && !node.classList.contains('MathJax') && !node.classList.contains('mat-fallback-rendered')) {
                const text = node.textContent || '';
                if (text.includes('$') || text.includes('\\') || node.querySelector('[class*="math"], [class*="formula"]')) {
                  scheduledNodes.add(node);
                  shouldProcess = true;
                }
              }
            }
          });
        }
      });

      if (shouldProcess && !rafId) {
        rafId = requestAnimationFrame(processScheduledNodes);
      }
    });

    observer.observe(document.body, { childList: true, subtree: true });
  }

  // Safety timer: If MathJax hasn't typeset within 600ms, run fallback to eliminate raw code
  setTimeout(() => {
    applyCleanFallbackMath(document.body);
  }, 600);

  // Initial typesetting upon DOM readiness
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      initMutationObserver();
      renderMath();
    });
  } else {
    initMutationObserver();
    renderMath();
  }

  window.addEventListener('load', function () {
    renderMath();
  });

})();
