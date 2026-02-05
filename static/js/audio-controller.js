// ====================================================================
// AUDIO CONTROLLER - Komunikasi dengan Audio Player Iframe
// Mengontrol BGM yang berjalan di iframe tersembunyi
// ====================================================================

class AudioController {
    constructor() {
        this.audioFrame = null;
        this.soundEffects = {};
        this.isReady = false;
        this.pendingCommands = [];
    }

    // Initialize audio controller
    init() {
        console.log('🎮 Audio Controller initializing...');

        // Get reference to audio iframe
        this.audioFrame = document.getElementById('audio-player-frame');

        if (!this.audioFrame) {
            console.error('❌ Audio player iframe not found!');
            return;
        }

        // Listen for messages from audio player iframe
        window.addEventListener('message', (event) => {
            if (event.data.source === 'audio-player') {
                this.handleAudioMessage(event.data);
            }
        });

        // Initialize sound effects
        this.initSoundEffects();

        console.log('🎮 Audio Controller initialized');
    }

    // Handle messages from audio player
    handleAudioMessage(message) {
        console.log('📨 Received from audio player:', message.type, message.data);

        switch (message.type) {
            case 'AUDIO_PLAYER_READY':
                this.isReady = true;
                console.log('✅ Audio player ready!');
                // Process pending commands
                this.processPendingCommands();
                break;

            case 'BGM_PLAYING':
                console.log('🎵 BGM is now playing');
                break;

            case 'BGM_STOPPED':
                console.log('🎵 BGM stopped');
                break;

            case 'BGM_ERROR':
                console.error('❌ BGM Error:', message.data);
                break;

            case 'STATUS':
                console.log('📊 BGM Status:', message.data);
                break;
        }
    }

    // Send command to audio player
    sendCommand(type, value = null) {
        if (!this.audioFrame) {
            console.error('❌ Audio frame not available');
            return;
        }

        const command = { type, value };

        if (!this.isReady) {
            // Queue command if iframe not ready yet
            console.log('⏳ Queueing command:', type);
            this.pendingCommands.push(command);
            return;
        }

        console.log('📤 Sending command to audio player:', type);
        this.audioFrame.contentWindow.postMessage(command, '*');
    }

    // Process queued commands
    processPendingCommands() {
        console.log('📦 Processing', this.pendingCommands.length, 'pending commands');
        while (this.pendingCommands.length > 0) {
            const command = this.pendingCommands.shift();
            this.sendCommand(command.type, command.value);
        }
    }

    // Initialize sound effects (non-BGM sounds)
    initSoundEffects() {
        this.soundEffects = {
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
        Object.values(this.soundEffects).forEach(sound => {
            sound.volume = 0.5; // 50% volume
            sound.preload = 'auto';
        });

        console.log('🔊 Sound effects initialized');
    }

    // Play BGM
    playBGM() {
        console.log('▶️ Play BGM command');
        this.sendCommand('PLAY_BGM');
    }

    // Stop BGM
    stopBGM() {
        console.log('⏸️ Stop BGM command');
        this.sendCommand('STOP_BGM');
    }

    // Set BGM volume (0.0 - 1.0)
    setVolume(volume) {
        console.log('🔊 Set volume:', volume);
        this.sendCommand('SET_VOLUME', volume);
    }

    // Get BGM status
    getStatus() {
        console.log('📊 Request status');
        this.sendCommand('GET_STATUS');
    }

    // Play sound effect
    playSound(soundName) {
        if (!this.soundEffects[soundName]) {
            console.warn(`⚠️ Sound "${soundName}" not found`);
            return;
        }

        const sound = this.soundEffects[soundName];
        sound.currentTime = 0; // Reset to beginning
        sound.play().catch(error => {
            console.log(`Could not play ${soundName}:`, error);
        });
    }

    // Enable audio (untuk bypass autoplay policy)
    enable() {
        console.log('🎵 Enabling audio...');
        this.playBGM();
    }
}

// Create global instance
const audioController = new AudioController();

// Auto-initialize when DOM ready
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for iframe to load
    setTimeout(() => {
        audioController.init();
    }, 500);
});

// Enable audio on first user interaction
let audioEnabled = false;
const enableAudioOnce = function() {
    if (!audioEnabled) {
        audioController.enable();
        audioEnabled = true;
        console.log('🎵 Audio enabled by user interaction');
    }
};

document.addEventListener('click', enableAudioOnce, { once: true });
document.addEventListener('touchstart', enableAudioOnce, { once: true });
document.addEventListener('keydown', enableAudioOnce, { once: true });

console.log('🎮 Audio Controller script loaded');