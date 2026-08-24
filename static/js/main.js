/**
 * AI Resume Screening Pro - Frontend JS Utilities
 */

document.addEventListener('DOMContentLoaded', function () {
  // Initialize file upload drag & drop if present
  initFileUpload();

  // Auto-dismiss alert notifications after 6 seconds
  setTimeout(function () {
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
      const bsAlert = new bootstrap.Alert(alert);
      bsAlert.close();
    });
  }, 6000);
});

/**
 * Handle File Upload Drag & Drop
 */
function initFileUpload() {
  const uploadZone = document.getElementById('uploadZone');
  const fileInput = document.getElementById('resume');
  const fileNameDisplay = document.getElementById('fileNameDisplay');

  if (!uploadZone || !fileInput) return;

  uploadZone.addEventListener('click', () => fileInput.click());

  ['dragenter', 'dragover'].forEach(eventName => {
    uploadZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      uploadZone.classList.add('dragover');
    }, false);
  });

  ['dragleave', 'drop'].forEach(eventName => {
    uploadZone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      uploadZone.classList.remove('dragover');
    }, false);
  });

  uploadZone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      fileInput.files = files;
      updateFileName(files[0].name);
    }
  });

  fileInput.addEventListener('change', () => {
    if (fileInput.files.length > 0) {
      updateFileName(fileInput.files[0].name);
    }
  });

  function updateFileName(name) {
    if (fileNameDisplay) {
      // textContent (not innerHTML) prevents HTML injection via crafted filenames
      fileNameDisplay.textContent = 'Selected file: ' + name;
      fileNameDisplay.classList.remove('d-none');
    }
  }
}

/**
 * Copy-to-clipboard for elements carrying a data-copy attribute.
 * Delegated so dynamically rendered buttons work too.
 */
document.addEventListener('click', function (e) {
  const copyBtn = e.target.closest('.copy-btn');
  if (!copyBtn) return;

  const text = copyBtn.getAttribute('data-copy') || '';
  const done = function () {
    const original = copyBtn.innerHTML;
    copyBtn.innerHTML = '<i class="bi bi-check-lg me-1"></i> Copied!';
    setTimeout(function () { copyBtn.innerHTML = original; }, 1500);
  };

  if (navigator.clipboard && navigator.clipboard.writeText) {
    navigator.clipboard.writeText(text).then(done).catch(function () { });
  } else {
    // Fallback for older browsers / non-secure contexts
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); done(); } catch (err) { }
    document.body.removeChild(ta);
  }
});

/**
 * Razorpay Payment Trigger Helper
 * Usage: onclick="initiateRazorpayPayment('pro', '{{ csrf_token() }}', this)"
 */
function initiateRazorpayPayment(plan, csrfToken, btnEl) {
  const btn = btnEl || (typeof event !== 'undefined' && event ? event.currentTarget : null);
  if (!btn) return;
  const originalText = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span> Processing...';

  fetch('/payment/create-order', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken
    },
    body: JSON.stringify({ plan: plan })
  })
    .then(res => res.json())
    .then(data => {
      if (!data.success) {
        btn.disabled = false;
        btn.innerHTML = originalText;
        alert(data.message || 'Payment initialization failed.');
        return;
      }

      // Razorpay options
      const options = {
        key: data.key_id,
        amount: data.amount,
        currency: data.currency,
        name: 'AI Resume Screening Pro',
        description: `${data.plan.toUpperCase()} Plan Subscription`,
        order_id: data.order_id,
        prefill: {
          name: data.user_name,
          email: data.user_email
        },
        theme: {
          color: '#3b82f6'
        },
        handler: function (response) {
          // Verify payment on server
          fetch('/payment/verify', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
              razorpay_order_id: response.razorpay_order_id,
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_signature: response.razorpay_signature,
              plan: plan
            })
          })
            .then(res => res.json())
            .then(verifyData => {
              if (verifyData.success) {
                window.location.href = verifyData.redirect_url || '/payment/success';
              } else {
                alert(verifyData.message || 'Payment verification failed.');
                btn.disabled = false;
                btn.innerHTML = originalText;
              }
            })
            .catch(function () {
              alert('Network error while verifying your payment. If you were charged, please contact support with your order ID.');
              btn.disabled = false;
              btn.innerHTML = originalText;
            });
        },
        modal: {
          ondismiss: function () {
            btn.disabled = false;
            btn.innerHTML = originalText;
          }
        }
      };

      const rzp = new Razorpay(options);
      rzp.open();
    })
    .catch(err => {
      console.error(err);
      btn.disabled = false;
      btn.innerHTML = originalText;
      alert('An unexpected error occurred. Please try again.');
    });
}
