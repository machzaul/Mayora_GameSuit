document.addEventListener('DOMContentLoaded', function() {
  const tapStart = document.getElementById('tapStart');
  
  if (tapStart) {
    tapStart.addEventListener('click', function() {
      // Play click sound if available
      const clickSound = new Audio('/static/assets/click.wav');
      clickSound.play().catch(e => console.log('Audio autoplay prevented'));
      
      // Show loading page
      window.location.href = '/loading';
    });
    
    // Also allow tap on main container
    document.querySelector('.container').addEventListener('click', function(e) {
      if (e.target !== tapStart && tapStart.contains(e.target) === false) {
        window.location.href = '/loading';
      }
    });
  }
});