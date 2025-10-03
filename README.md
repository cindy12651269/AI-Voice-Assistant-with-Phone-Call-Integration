# AI Voice Assistant with Phone Call Integration

> Production-ready template for **real-time voice AI** over **web** and **phone**, built on top of LangChain’s `react-voice-agent`. This top section introduces the project for proposals while development continues.

## Project Highlights

* **New repo bootstrap**: pulled from `langchain-ai/react-voice-agent`, rebranded, cleaned, history preserved.
* **Voice pipeline optimization**: WebRTC + OpenAI Realtime API, pluggable **ASR/TTS** (OpenAI/Deepgram/ElevenLabs/Azure), latency instrumentation (P50/P95).
* **Telephony integration**: **Twilio Programmable Voice** + SIP.js bridge, DTMF passthrough.
* **WebRTC mode**: one-to-one **Browser ↔ AI Voice Assistant** demo (low-latency).
* **Demo available**: Browser Voice interaction + Phone Call (Twilio). *(See "Demo" section below.)*

## Tech stack

* **Languages**: TypeScript (React/Node.js), Python (optional server tools)
* **Voice**: WebRTC (UDP-first), OpenAI Realtime API; ASR/TTS adapters: OpenAI / Deepgram / ElevenLabs / Azure Speech
* **Telephony**: Twilio Programmable Voice, SIP.js, TwiML; WebSocket media bridge
* **Dev**: Next.js, LangChain.js, Node.js perf hooks, WebRTC Stats API

# Architecture

**Client (Browser)**  
- Microphone & Speaker  
- WebRTC connection (UDP-first)  

**Phone (PSTN / Mobile)**  
- Standard phone call  
- DTMF inputs  

**Edge / Server (Node.js)**  
- Web Server / WebSocket Bridge  
- Telephony Bridge (Twilio SIP / TwiML)  

**AI Backend**  
- OpenAI Realtime API  
  - Streaming ASR (speech-to-text)  
  - LLM reasoning  
  - TTS (text-to-speech)  
- LangChain Tools (optional)  
  - CRM, Accounting, News, Sentiment  

**Data Flow**  
1. **WebRTC mode (Browser ↔ AI)**  
   - Browser → WebSocket Bridge → OpenAI Realtime → Tools  
   - Audio response back to browser  

2. **Telephony mode (Phone ↔ AI)**  
   - Phone → Twilio SIP/TwiML → Telephony Bridge → WebSocket Bridge → OpenAI Realtime → Tools  
   - Audio response back to phone  

## Demo

* **Browser Voice**: *link-to-video-or-gif*
* **Phone Call (Twilio)**: *link-to-video-or-gif*

---

## 🦜🎤 Voice ReAct Agent

This is an implementation of a [ReAct](https://arxiv.org/abs/2210.03629)-style agent that uses OpenAI's new [Realtime API](https://platform.openai.com/docs/guides/realtime).

Specifically, we enable this model to call tools by providing it a list of [LangChain tools](https://python.langchain.com/docs/how_to/custom_tools/#creating-tools-from-functions). It is easy to write custom tools, and you can easily pass these to the model.

![](static/react.png)

## 📜 License & Credits

This section of the project is originally from
[langchain-ai/react-voice-agent](https://github.com/langchain-ai/react-voice-agent/tree/main)

It has been **modified and extended** into the current repository
**AI Voice Assistant with Phone Call Integration**,
with additional features (telephony, dual-mode WebRTC/LiveKit, memory, observability, etc.).

Please keep the original LICENSE from LangChain intact.

All modifications in this repository are provided under the same license as the upstream project, unless otherwise noted.

## Installation

### Python

Make sure you're running Python 3.10 or later, then install `uv` to be able to run the project:

```bash
pip install uv
```

And make sure you have both `OPENAI_API_KEY` and `TAVILY_API_KEY` environment variables set up.

```bash
export OPENAI_API_KEY=your_openai_api_key
export TAVILY_API_KEY=your_tavily_api_key
```

Note: the Tavily API key is for the Tavily search engine, you can get an API key [here](https://app.tavily.com/). This is just an example tool, and if you do not want to use it you do not have to (see [Adding your own tools](#adding-your-own-tools))

### TypeScript

Navigate into the `js_server` folder, then install required dependencies with `yarn`:

```bash
yarn
```

You will also need to copy the provided `js_server/.env.example` file to `.env` and fill in your OpenAI and Tavily keys.

## Running the project

### Python

To run the project, execute the following commands:

```bash
cd server
uv run python -m src.server.app
```

### TypeScript

```bash
cd js_server
yarn dev
```

## Open the browser

Now you can open the browser and navigate to `http://localhost:3000` to see the project running.

### Enable microphone

You may need to make sure that your browser can access your microphone.

- [Chrome](http://0.0.0.0:3000/)

## Adding your own tools

You can add your own tools by adding them to the `server/src/server/tools.py` file for Python or the `js_server/src/tools.ts` folder for TypeScript.

## Adding your own custom instructions

You can add your own custom instructions by adding them to the `server/src/server/prompt.py` file for Python or the `js_server/src/prompt.ts` folder for TypeScript.

## Errors

- `WebSocket connection: HTTP 403`
  - This error is due to account permissions from OpenAI side, your account/org doesn't have api access to Realtime API or insufficient funds.
  - check if you have Realtime API access in the playground [here](https://platform.openai.com/playground/realtime).

## Next steps

- [ ] Enable interrupting the AI
- [ ] Enable changing of instructions/tools based on state

---

## ✅ Speech Pipeline Optimization (WebRTC + ASR/TTS)

This project supports two modes:

* **Local Development Mode** — for testing OpenAI ASR/TTS latency and WebRTC audio pipeline.
* **Cloud Deployment Mode (Render)** — for Twilio webhook or public demo access.

---

### 🧩 1. Local Development Mode

#### Step 0 — Activate Virtual Environment

Before starting, make sure to activate the virtual environment:

```bash
source .venv/bin/activate
```

#### Step 1 — Set ASR/TTS Providers

The default configuration uses **OpenAI Realtime ASR and TTS**.
You can override the provider by setting the following environment variables:

**macOS / Linux (zsh/bash):**

```bash
export ASR_PROVIDER=openai
export TTS_PROVIDER=openai
```

**Windows (PowerShell):**

```powershell
$env:ASR_PROVIDER="openai"
$env:TTS_PROVIDER="openai"
```

> Optional providers (with API keys):
> ASR – `deepgram`
> TTS – `elevenlabs`, `azure`

#### Step 2 — Start the Python Server

```bash
cd src
uv run python -m server.app
```

Expected logs:

```
Uvicorn running on http://0.0.0.0:8000
```

#### Step 3 — Frontend Configuration (.env Management)

For the frontend (`js_server`), create two environment files to easily switch between local and cloud modes:

**.env.local**

```bash
VITE_SERVER_URL=http://localhost:8000
```

**.env.render**

```bash
VITE_SERVER_URL=https://ai-voice-assistant-with-phone-call.onrender.com
```

Switch between modes by copying the desired file:

```bash
cp js_server/.env.local js_server/.env       # Local Mode
```

Then start the frontend:

```bash
cd js_server
yarn dev
```

Expected logs:

```
Server is running on http://localhost:3000
```

Then open the browser at **[http://localhost:3000](http://localhost:3000)**

→ Allow microphone access
→ Click **Start Audio** to begin WebRTC voice testing.

#### Step 4 — Verify ASR/TTS Output

Speak into the mic and check the Python server console:

```
Transcribed: 'transcribed text from OpenAI'
LLM processing skipped (test mode)
Synthesized audio (OpenAI)
```

If Deepgram or ElevenLabs keys are set, the output will switch automatically:

```
Transcribed: "hello world"        # Deepgram
Synthesized audio (ElevenLabs)    # ElevenLabs
```

#### Step 5 — Check Latency Logs

**Backend (Python server)**
Each stage timing is printed to the console:

```
ASR latency: 0.003s
LLM latency: 0.052s
TTS latency: 0.020s
```

Latency metrics are handled by `log_stage_latency()` in `server/src/server/utils.py`.

**Frontend (Browser / DevTools)**
Open Chrome DevTools (**F12**) → Console → check WebRTC statistics:

* `packetsSent`
* `jitter`
* `rtt`

---

### ☁️ 2. Cloud Deployment Mode (Render + Twilio Integration)

If you have deployed the backend to **Render**, use this mode for remote access or Twilio webhook testing.

#### Step 1 — Confirm Deployment

Render backend URL (example):

```
https://ai-voice-assistant-with-phone-call.onrender.com
```

Server log example:

```
Uvicorn running on http://0.0.0.0:10000 (Render managed)
```

#### Step 2 — Configure Twilio Webhook

In Twilio Console → **Phone Numbers → Manage → Active Numbers**,
set **A CALL COMES IN** → **Webhook** to:

```
https://ai-voice-assistant-with-phone-call.onrender.com/twilio/voice
```

#### Step 3 — Frontend Configuration

Ensure `.env.render` is active:

```bash
cp js_server/.env.render js_server/.env     # Cloud Mode
cd js_server
yarn dev
```

Expected logs:

```
Server is running on http://localhost:3000
```

The browser demo will now connect to the **Render backend** instead of local `localhost:8000`.

#### Step 4 — Public Showcase 

* Call your Twilio number to test the AI agent.
* Render server handles the `/twilio/voice` webhook request.
* The AI pipeline (ASR → LLM → TTS) responds in real time.

---

### 📊 Summary

| Mode                  | Backend                   | Frontend              | Default Providers       | Use Case                                 |
| --------------------- | ------------------------- | --------------------- | ----------------------- | ---------------------------------------- |
| **Local Development** | `localhost:8000`          | `localhost:3000`      | OpenAI ASR + OpenAI TTS | Latency tuning & speech pipeline testing |
| **Cloud (Render)**    | `https://...onrender.com` | optional (via `.env`) | OpenAI ASR + OpenAI TTS | Twilio Webhook & Upwork Showcase         |

---

# 📞 Telephony Integration (Twilio / SIP)

This section documents the end-to-end steps for integrating telephony with the AI Voice Assistant using Twilio and SIP.

## Phone Number & Voice Webhook

* **Action**: Purchase or use a Twilio phone number.
* **Configure**: Twilio Console → Phone Numbers → Voice → *A CALL COMES IN* → Webhook.
* **URL**:

  ```
  https://ai-voice-assistant-with-phone-call.onrender.com/twilio/voice
  ```
* **HTTP Method**: POST
* **Validation**: Incoming call can be routed to the webhook.
* **Acceptance Criteria**: Server log shows webhook hit.

## Minimal Webhook Response

* **Code**: `app.py` → `/twilio/voice` route with TwiML `<Say>`.

* **Test**: Open in browser:

  ```
  https://ai-voice-assistant-with-phone-call.onrender.com/twilio/voice
  ```

* **Expected Output (initial minimal version)**:

  ```xml
  <Response>
    <Say language="en-US" voice="alice">
      Hello from your AI Voice Agent. The webhook is connected.
    </Say>
  </Response>
  ```

* **Current Implementation**: The code has been upgraded to return TwiML with `<Stream>` (for audio streaming) in addition to `<Say>`.

* **Acceptance Criteria**: Render logs show:

  ```
  ✅ [/twilio/voice] Incoming request received
     ↳ Method: POST
     ↳ Form data: {...}
     ↳ Responding with TwiML <Stream> + <Say>
  ```

## Media Streams Processing

* **Action**: Add TwiML `<Stream>` to forward live audio.
* **Server**: Implement WebSocket handler to receive audio.
* **Audio Handling**: µ-law → PCM/WAV conversion.
* **Acceptance Criteria**: Logs confirm streaming events received, e.g.:

  ```
  🎧 Twilio Media Stream connected
  🎤 Received audio chunk: ulaw=160, pcm=320
  ```

## DTMF Input Handling

* **Action**: Use Media Stream `dtmf` event to detect keypad input.
* **Event**: Log DTMF tone events during active call.
* **Acceptance Criteria**: Logs confirm digit pressed (e.g., `🎹 DTMF received: 1`).

## Outbound Call Demo

* **Option A**: Run locally

  ```bash
  python src/server/make_call.py
  ```
* **Option B**: Trigger via Render API route

  ```
  GET https://ai-voice-assistant-with-phone-call.onrender.com/callme
  ```
* **Expected**: Twilio Call Logs show outbound call; Render logs confirm webhook triggered.
* **Acceptance Criteria**: Outbound call log present in Twilio Console.

## SIP.js Web Softphone

* **Action**: Configure SIP.js client in browser.
* **Connect**: Twilio Voice → SIP.js endpoint.
* **Test**: Call from browser → AI Voice Agent.
* **Acceptance Criteria**: Two-way audio established between browser and server.

## ⚠️ Notes

* For demo purposes, validation relies on Render logs + Twilio Call Logs.
* **Inbound calling to Taiwan mobiles may fail** due to local carrier restrictions (STIR/SHAKEN filtering). This is expected even on paid accounts.
* **Outbound calling works reliably** once Caller ID is verified.
* For portfolio/demo purposes, outbound calls (via `/callme`) or Twilio numbers from Hong Kong (+852) or Singapore (+65) are recommended for cross-border reliability.
* Official Twilio call recording (`<Dial record=...>`) is incompatible with `<Connect><Stream>`. The future implementation will migrate to **Conference Recording** for combined AI stream + official recording support.

---

## 🌐 WebRTC Mode (Browser Voice Agent)

1) **Start Python server** (same as M1).

2) **Start JS demo** (same as M1), then open http://localhost:3000.

3) **Speak into the mic** and observe the end-to-end loop:
- Expected server logsㄦ
```
Received audio stream
Transcribed: "what's the weather"
AI Response: "The weather is sunny."
Synthesized audio (bytes: 9021)
```
- Browser should play back the AI voice response.

4) **Validate metrics**
- Server logs show latency breakdown (ASR → LLM → TTS).
- Browser console shows WebRTC stats (jitter, packets, rtt). Capture a short screen recording or screenshot for your README.

---

### ✅ Pass Criteria Summary

- **Speech Pipeline Optimization (WebRTC + ASR/TTS)**: Browser demo works; ASR/TTS provider switching via env; server & browser print latency/stats.
- **Telephony Integration (Twilio / SIP)**: Inbound phone call reaches your server; you hear AI audio back; server logs show telephony flow.
- **WebRTC Mode (Browser Voice Agent)**: Full WebRTC 1:1 loop from browser mic to AI reply (audio playback) with visible latency metrics.

