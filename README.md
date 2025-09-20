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
* **Dev**: Next.js/Vite, LangChain.js, Node.js perf hooks, WebRTC Stats API

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
uv run src/server/app.py
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