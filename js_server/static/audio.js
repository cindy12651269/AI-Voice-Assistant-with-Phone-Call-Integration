// =============================================
// 🎧 audio.js
// Handles microphone input and WebSocket playback
// =============================================

// Auto-detect WebSocket URL (Render or localhost)
const WS_URL =
  window.location.hostname === "localhost"
    ? "ws://localhost:8000/ws"
    : `wss://${window.location.host.replace("3000", "8000")}/ws`;

// Constant buffer size for audio streaming
const BUFFER_SIZE = 4800;

// ----------------------------------------------------
// 🔊 Audio Player (Speaker playback from AI response)
// ----------------------------------------------------
class Player {
  constructor() {
    this.playbackNode = null;
    this.audioContext = null;
  }

  async init(sampleRate = 24000) {
    this.audioContext = new AudioContext({ sampleRate });
    // Load custom audio worklet processor
    await this.audioContext.audioWorklet.addModule("/static/audio-playback-worklet.js");

    this.playbackNode = new AudioWorkletNode(this.audioContext, "audio-playback-worklet");
    this.playbackNode.connect(this.audioContext.destination);

    console.log("🎧 Player initialized at sampleRate:", sampleRate);
  }

  play(buffer) {
    if (this.playbackNode) {
      this.playbackNode.port.postMessage(buffer);
    }
  }

  stop() {
    if (this.playbackNode) {
      this.playbackNode.port.postMessage(null);
    }
  }
}

// ----------------------------------------------------
// 🎙️ Audio Recorder (Microphone → WebSocket input)
// ----------------------------------------------------
class Recorder {
  constructor(onDataAvailable) {
    this.onDataAvailable = onDataAvailable;
    this.audioContext = null;
    this.mediaStream = null;
    this.workletNode = null;
  }

  async start(stream) {
    try {
      if (this.audioContext) {
        await this.audioContext.close();
      }

      // Initialize 24kHz mic context
      this.audioContext = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 24000,
      });

      // Load the processor
      await this.audioContext.audioWorklet.addModule("/static/audio-processor-worklet.js");

      this.mediaStream = stream;
      const source = this.audioContext.createMediaStreamSource(this.mediaStream);
      this.workletNode = new AudioWorkletNode(this.audioContext, "audio-processor-worklet");

      // Receive PCM chunks
      this.workletNode.port.onmessage = (event) => {
        this.onDataAvailable(event.data.buffer);
      };

      source.connect(this.workletNode);
      this.workletNode.connect(this.audioContext.destination);

      console.log("🎤 Recorder started.");
    } catch (error) {
      console.error("❌ Recorder start error:", error);
      this.stop();
    }
  }

  async stop() {
    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    if (this.audioContext) {
      await this.audioContext.close();
      this.audioContext = null;
    }

    console.log("🛑 Recorder stopped.");
  }
}

// ----------------------------------------------------
// 🔁 Combined Flow: Mic → WebSocket → Speaker
// ----------------------------------------------------
async function startAudio() {
  try {
    const ws = new WebSocket(WS_URL);
    const player = new Player();
    await player.init(24000);

    // WebSocket: handle AI response audio
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data?.type !== "response.audio.delta") return;

      const bytes = Uint8Array.from(atob(data.delta), (c) => c.charCodeAt(0));
      const pcm = new Int16Array(bytes.buffer);
      player.play(pcm);
    };

    // Create mic recorder
    let buffer = new Uint8Array();
    const appendBuffer = (newData) => {
      const tmp = new Uint8Array(buffer.length + newData.length);
      tmp.set(buffer);
      tmp.set(newData, buffer.length);
      buffer = tmp;
    };

    const handleAudio = (data) => {
      const uint8 = new Uint8Array(data);
      appendBuffer(uint8);

      // Send when we reach buffer threshold
      if (buffer.length >= BUFFER_SIZE) {
        const chunk = buffer.slice(0, BUFFER_SIZE);
        buffer = buffer.slice(BUFFER_SIZE);

        ws.send(
          JSON.stringify({
            type: "input_audio_buffer.append",
            audio: btoa(String.fromCharCode(...chunk)),
          })
        );
      }
    };

    // Get microphone permission
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const recorder = new Recorder(handleAudio);
    await recorder.start(stream);

    console.log("🎙️ Audio streaming started →", WS_URL);
  } catch (err) {
    console.error("❌ Error starting audio:", err);
    alert("Microphone access failed. Please check permissions.");
  }
}

// ----------------------------------------------------
// 🎛️ Button toggle logic
// ----------------------------------------------------
const toggleButton = document.getElementById("toggleAudio");
let isAudioOn = false;

toggleButton.addEventListener("click", async () => {
  if (!isAudioOn) {
    await startAudio();
    toggleButton.textContent = "Stop Audio";
    isAudioOn = true;
  } else {
    toggleButton.textContent = "Start Audio";
    isAudioOn = false;
  }
});
