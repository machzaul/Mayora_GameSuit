document.addEventListener('DOMContentLoaded', function() {
  const tapStart = document.getElementById('tapStart');
  if (!tapStart) return;

  function navigate(path) {
    if (window.parent && window.parent !== window) {
      window.parent.postMessage({ type: 'nav', url: path }, '*');
    } else {
      window.location.href = path;
    }
  }

  tapStart.addEventListener('click', function() {
    if (window.audioManager && window.audioManager.enableAudio) {
      window.audioManager.enableAudio();
    }
    navigate('/loading');
  });

  const container = document.querySelector('.container');
  if (container) {
    container.addEventListener('click', function(e) {
      if (e.target !== tapStart && tapStart.contains(e.target) === false) {
        navigate('/loading');
      }
    });
  }
});
