class PcmCaptureProcessor extends AudioWorkletProcessor {
  constructor(options) {
    super();
    this.targetSampleRate = options?.processorOptions?.targetSampleRate || 16000;
    this.inputGain = options?.processorOptions?.inputGain || 1;
    this.inputSampleRate = sampleRate;
  }

  downsampleBuffer(buffer, inputRate, outputRate) {
    if (outputRate === inputRate) {
      return buffer;
    }
    const ratio = inputRate / outputRate;
    const newLength = Math.round(buffer.length / ratio);
    const result = new Float32Array(newLength);
    let offsetResult = 0;
    let offsetBuffer = 0;
    while (offsetResult < result.length) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio);
      let accum = 0;
      let count = 0;
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i];
        count++;
      }
      result[offsetResult] = count > 0 ? accum / count : 0;
      offsetResult++;
      offsetBuffer = nextOffsetBuffer;
    }
    return result;
  }

  toInt16PCM(float32Buffer) {
    const pcm = new Int16Array(float32Buffer.length);
    for (let i = 0; i < float32Buffer.length; i++) {
      const s = Math.max(-1, Math.min(1, Math.tanh(float32Buffer[i] * this.inputGain)));
      pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return pcm;
  }

  process(inputs) {
    const input = inputs[0];
    if (!input || input.length === 0) {
      return true;
    }
    const channels = input.filter((channel) => channel && channel.length > 0);
    if (channels.length === 0) {
      return true;
    }
    const sampleLength = channels[0].length;
    const mono = new Float32Array(sampleLength);
    for (let ch = 0; ch < channels.length; ch += 1) {
      const data = channels[ch];
      for (let i = 0; i < sampleLength; i += 1) {
        mono[i] += data[i];
      }
    }
    for (let i = 0; i < sampleLength; i += 1) {
      mono[i] /= channels.length;
    }
    const downsampled = this.downsampleBuffer(
      mono,
      this.inputSampleRate,
      this.targetSampleRate
    );
    const pcm16 = this.toInt16PCM(downsampled);
    this.port.postMessage(pcm16.buffer, [pcm16.buffer]);
    return true;
  }
}

registerProcessor("pcm-capture-processor", PcmCaptureProcessor);
