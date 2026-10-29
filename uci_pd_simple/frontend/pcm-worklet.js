class PCMCollector extends AudioWorkletProcessor {
  constructor() {
    super();
    this.active = true;
    this.buffer = new Float32Array(2048);
    this.used = 0;
    this.port.onmessage = event => {
      if (event.data === 'stop') {
        this.flush();
        this.active = false;
        this.port.postMessage({type: 'stopped'});
      }
    };
  }
  flush() {
    if (this.used) {
      const chunk = this.buffer.slice(0, this.used);
      this.port.postMessage({type: 'pcm', chunk}, [chunk.buffer]);
      this.used = 0;
    }
  }
  process(inputs) {
    if (!this.active) return false;
    const channels = inputs[0];
    if (!channels?.length) return true;
    for (let i = 0; i < channels[0].length; i++) {
      let sample = 0;
      for (const channel of channels) sample += channel[i] || 0;
      this.buffer[this.used++] = sample / channels.length;
      if (this.used === this.buffer.length) this.flush();
    }
    // Outputs remain silent: no microphone feedback to speakers.
    return true;
  }
}
registerProcessor('pcm-collector', PCMCollector);
