(function () {
  let isBound = false;
  const queuedCalls = [];

  function bindParentAudio() {
    if (window.parent && window.parent !== window && window.parent.audioManager) {
      window.audioManager = window.parent.audioManager;
      isBound = true;
      flushQueue();
      return true;
    }
    return false;
  }

  function flushQueue() {
    if (!isBound) return;
    while (queuedCalls.length) {
      const fn = queuedCalls.shift();
      try { fn(); } catch (_) {}
    }
  }

  function queueOrRun(fn) {
    if (isBound) {
      fn();
    } else {
      queuedCalls.push(fn);
    }
  }

  const proxy = {
    init: function () { queueOrRun(() => window.parent.audioManager.init()); },
    playBGM: function () { queueOrRun(() => window.parent.audioManager.playBGM()); },
    stopBGM: function () { queueOrRun(() => window.parent.audioManager.stopBGM()); },
    play: function (name) { queueOrRun(() => window.parent.audioManager.play(name)); },
    enableAudio: function () { queueOrRun(() => window.parent.audioManager.enableAudio()); }
  };

  if (!bindParentAudio() && window.audioManager) {
    return;
  }

  if (!window.audioManager) {
    window.audioManager = proxy;
  }

  window.addEventListener('load', bindParentAudio);

  // Play click on every user click inside iframe (only when bound)
  document.addEventListener('click', () => {
    if (isBound && window.audioManager && window.audioManager.play) {
      window.audioManager.play('click');
    }
  }, true);
})();
