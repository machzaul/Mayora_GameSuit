// Audio Manager for Fortune Hands Game
class AudioManager {
    constructor() {
        this.sounds = {};
        this.bgm = null;
        this.initialized = false;
    }

    // Initialize all audio files
    init() {
        if (this.initialized) return;

        // Background Music (loop)
        this.bgm = new Audio('/static/assets/sound/bgm-fortune-hands.mp3');
        this.bgm.loop = true;
        this.bgm.volume = 0.3; // 30% volume agar tidak terlalu keras

        // Sound Effects
        this.sounds = {
            click: new Audio('/static/assets/sound/click.wav'),
            countdown: new Audio('/static/assets/sound/countdown.wav'),
            draw: new Audio('/static/assets/sound/draw-round.wav'),
            lose: new Audio('/static/assets/sound/lost-round.wav'),
            win: new Audio('/static/assets/sound/win-round.wav'),
            paperScroll: new Audio('/static/assets/sound/paper-scroll.wav'),
            soClose: new Audio('/static/assets/sound/so-close.wav'),
            youWin: new Audio('/static/assets/sound/you-win.wav'),
            handDetected: new Audio('/static/assets/sound/hand-detected.wav')
        };

        // Set volume untuk semua sound effects
        Object.values(this.sounds).forEach(sound => {
            sound.volume = 0.5; // 50% volume
        });

        this.initialized = true;
        console.log('🎵 Audio Manager initialized');
    }

    // Play background music
    playBGM() {
        if (!this.bgm) return;
        
        this.bgm.play().catch(error => {
            console.log('BGM autoplay prevented, will play on user interaction');
        });
    }

    // Stop background music
    stopBGM() {
        if (this.bgm) {
            this.bgm.pause();
            this.bgm.currentTime = 0;
        }
    }

    // Play sound effect
    play(soundName) {
        if (!this.sounds[soundName]) {
            console.warn(`Sound "${soundName}" not found`);
            return;
        }

        const sound = this.sounds[soundName];
        sound.currentTime = 0; // Reset to beginning
        sound.play().catch(error => {
            console.log(`Could not play ${soundName}:`, error);
        });
    }

    // Enable audio on user interaction (untuk bypass autoplay policy)
    enableAudio() {
        this.init();
        this.playBGM();
    }
}

// Create global audio manager instance
const audioManager = new AudioManager();
// Expose for iframe access
window.audioManager = audioManager;

// Auto-enable audio on first user interaction
document.addEventListener('click', function enableAudioOnClick() {
    audioManager.enableAudio();
    document.removeEventListener('click', enableAudioOnClick);
}, { once: true });
