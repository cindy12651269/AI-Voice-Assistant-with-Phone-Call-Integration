// source: https://github.com/Azure-Samples/aisearch-openai-rag-audio/blob/7f685a8969e3b63e8c3ef345326c21f5ab82b1c3/app/frontend/public/audio-processor-worklet.js
// Audio Playback Worklet with timestamp logging
class AudioPlaybackWorklet extends AudioWorkletProcessor {
    constructor() {
        super();
        this.port.onmessage = this.handleMessage.bind(this);
        this.buffer = [];
        this.lastTimestamp = null;
    }

    handleMessage(event) {
        if (event.data === null) {
            this.buffer = [];
            return;
        }

        // Handle timestamp header 
        if (event.data.ts && event.data.data) {
            const now = currentTime * 1000; // in ms
            const latency = now - event.data.ts;
            console.log(`[AudioLatency] ${latency.toFixed(2)} ms`);

            this.lastTimestamp = event.data.ts;
            this.buffer.push(...event.data.data);
        } else {
            // backward compatibility (raw Int16Array)
            this.buffer.push(...event.data);
        }
    }

    process(inputs, outputs, parameters) {
        const output = outputs[0];
        const channel = output[0];

        if (this.buffer.length > channel.length) {
            const toProcess = this.buffer.slice(0, channel.length);
            this.buffer = this.buffer.slice(channel.length);
            channel.set(toProcess.map(v => v / 32768));
        } else {
            channel.set(this.buffer.map(v => v / 32768));
            this.buffer = [];
        }

        return true;
    }
}

registerProcessor("audio-playback-worklet", AudioPlaybackWorklet);

