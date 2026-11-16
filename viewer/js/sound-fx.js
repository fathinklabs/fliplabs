/**
 * FlipLabs Realistic Paper Turn Sound & Ambient Study BGM Engine (Web Audio API)
 * Zero external audio dependency required — generates crisp realistic paper rustle on the fly.
 */
class FlipSoundEngine {
  constructor() {
    this.ctx = null;
    this.enabled = true;
    this.bgmPlaying = false;
    this.bgmInterval = null;
  }

  initContext() {
    if (!this.ctx) {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) this.ctx = new AudioCtx();
    }
    if (this.ctx && this.ctx.state === 'suspended') {
      this.ctx.resume();
    }
  }

  playFlip() {
    if (!this.enabled) return;
    try {
      this.initContext();
      if (!this.ctx) return;

      const duration = 0.22;
      const sampleRate = this.ctx.sampleRate;
      const frameCount = Math.floor(sampleRate * duration);
      const buffer = this.ctx.createBuffer(1, frameCount, sampleRate);
      const data = buffer.getChannelData(0);

      // Filtered white noise shaped like a crisp textbook page turn
      for (let i = 0; i < frameCount; i++) {
        const t = i / frameCount;
        const envelope = Math.sin(t * Math.PI) * Math.pow(1 - t, 1.3);
        data[i] = (Math.random() * 2 - 1) * envelope * 0.28;
      }

      const source = this.ctx.createBufferSource();
      source.buffer = buffer;

      const filter = this.ctx.createBiquadFilter();
      filter.type = 'bandpass';
      filter.frequency.setValueAtTime(1100, this.ctx.currentTime);
      filter.frequency.exponentialRampToValueAtTime(2400, this.ctx.currentTime + duration);
      filter.Q.value = 1.4;

      const gain = this.ctx.createGain();
      gain.gain.setValueAtTime(0.42, this.ctx.currentTime);

      source.connect(filter);
      filter.connect(gain);
      gain.connect(this.ctx.destination);
      source.start();
    } catch (e) {
      // Ignore autoplay restrictions before first interaction
    }
  }

  toggleFlipSound() {
    this.enabled = !this.enabled;
    return this.enabled;
  }
}

window.flipSound = new FlipSoundEngine();
