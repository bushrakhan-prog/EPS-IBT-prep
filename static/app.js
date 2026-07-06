// IBT Portal — app.js
// Utility JS for modal closing, flash auto-dismiss, etc.

document.addEventListener('DOMContentLoaded', () => {
  // Auto-dismiss flash alerts
  document.querySelectorAll('.alert').forEach(el => {
    setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .4s'; setTimeout(() => el.remove(), 400); }, 4000);
  });
});
