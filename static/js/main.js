/**
 * MAT-VLAB — Main Global Utilities
 */

// Toast notification helper
function showToast(message, type = 'info') {
  let toastContainer = document.getElementById('toast-container');
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    toastContainer.style.zIndex = '9999';
    document.body.appendChild(toastContainer);
  }

  const bgClass = type === 'success' ? 'bg-success text-white' :
                  type === 'danger' || type === 'error' ? 'bg-danger text-white' :
                  type === 'warning' ? 'bg-warning text-dark' : 'bg-primary text-white';

  const toastEl = document.createElement('div');
  toastEl.className = `toast align-items-center ${bgClass} border-0 show shadow-lg mb-2`;
  toastEl.setAttribute('role', 'alert');
  toastEl.setAttribute('aria-live', 'assertive');
  toastEl.setAttribute('aria-atomic', 'true');

  toastEl.innerHTML = `
    <div class="d-flex">
      <div class="toast-body fw-semibold">
        ${message}
      </div>
      <button type="button" class="btn-close ${type === 'warning' ? '' : 'btn-close-white'} me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
    </div>
  `;

  toastContainer.appendChild(toastEl);
  setTimeout(() => {
    toastEl.classList.remove('show');
    setTimeout(() => toastEl.remove(), 300);
  }, 4000);
}

// Format numbers nicely
function formatNumber(num, decimals = 2) {
  if (num === null || num === undefined || isNaN(num)) return 'N/A';
  return Number(num).toLocaleString(undefined, {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  });
}

// Download Sample CSV Helper
function downloadSampleCSV() {
  const csvContent = "Reading,Load_N,Extension_mm\n" +
    "1,0,0.000\n" +
    "2,2500,0.008\n" +
    "3,5000,0.016\n" +
    "4,7500,0.023\n" +
    "5,10000,0.031\n" +
    "6,12500,0.039\n" +
    "7,15000,0.047\n" +
    "8,17500,0.055\n" +
    "9,19500,0.061\n" +
    "10,19800,0.085\n" +
    "11,19400,0.180\n" +
    "12,19500,0.320\n" +
    "13,19600,0.500\n" +
    "14,20800,0.850\n" +
    "15,22500,1.350\n" +
    "16,25200,2.100\n" +
    "17,28400,3.150\n" +
    "18,31200,4.400\n" +
    "19,33100,5.700\n" +
    "20,34200,7.100\n" +
    "21,34500,8.200\n" +
    "22,34200,9.500\n" +
    "23,33000,10.800\n" +
    "24,31100,12.100\n" +
    "25,28600,13.400\n" +
    "26,26200,14.200\n";

  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', 'mat_vlab_tensile_sample.csv');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  showToast('Sample CSV template downloaded successfully!', 'success');
}

// Global mobile enhancements on DOM ready
document.addEventListener('DOMContentLoaded', () => {
  // 1. Auto-close mobile hamburger menu when a link is clicked
  const navCollapse = document.getElementById('navbarMain');
  if (navCollapse) {
    const navLinks = navCollapse.querySelectorAll('.nav-link:not(.dropdown-toggle), .dropdown-item');
    navLinks.forEach(link => {
      link.addEventListener('click', () => {
        if (window.innerWidth < 992 && navCollapse.classList.contains('show')) {
          const bsCollapse = bootstrap.Collapse.getInstance(navCollapse) || new bootstrap.Collapse(navCollapse, { toggle: false });
          bsCollapse.hide();
        }
      });
    });
  }

  // 2. Global responsive resize for all Plotly graphs
  let resizeTimeout = null;
  const triggerPlotlyResize = () => {
    document.querySelectorAll('.js-plotly-plot').forEach(plotEl => {
      if (typeof Plotly !== 'undefined' && plotEl && plotEl.data) {
        Plotly.Plots.resize(plotEl);
      }
    });
  };

  window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(triggerPlotlyResize, 100);
  });

  window.addEventListener('orientationchange', () => {
    setTimeout(triggerPlotlyResize, 200);
  });
});
