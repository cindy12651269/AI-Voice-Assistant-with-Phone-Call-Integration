from dotenv import load_dotenv
load_dotenv()

import os
import time
import uvicorn
import base64
import wave
from datetime import datetime
import numpy as np          # for PCM16 buffer handling
import g711                 # μ-law <-> PCM helpers

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, PlainTextResponse
from starlette.routing import Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket
from starlette.responses import FileResponse

from src.langchain_openai_voice import OpenAIVoiceReactAgent
from src.server.utils import websocket_stream
from src.server.prompt import INSTRUCTIONS
from src.server.tools import TOOLS

# Import provider factories from utils.py 
from src.langchain_openai_voice.utils import get_asr_provider, get_tts_provider

# Import Twilio VoiceResponse to generate TwiML
from twilio.twiml.voice_response import VoiceResponse, Start, Gather
from twilio.rest import Client

# PUBLIC_URL (must include https:// in .env)
PUBLIC_URL = os.getenv("PUBLIC_URL")
if not PUBLIC_URL:
    raise ValueError("PUBLIC_URL is not set. Please add it to your .env (e.g. https://your-service.onrender.com)")

# Directory for server-side recordings (ephemeral on Render; persists until redeploy)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")
os.makedirs(RECORDINGS_DIR, exist_ok=True) # Create if not exists

# Browser WebSocket endpoint (ASR → LLM → TTS pipeline)
# Receive audio from the browser, and stream the response back to the client.
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept() # Stream of audio input from browser
    browser_receive_stream = websocket_stream(websocket)

    # Choose ASR and TTS providers from env vars (default = openai)
    asr_provider = get_asr_provider(os.getenv("ASR_PROVIDER", "openai"))
    tts_provider = get_tts_provider(os.getenv("TTS_PROVIDER", "openai"))

    # Create the LLM Agent
    agent = OpenAIVoiceReactAgent(
        model="gpt-4o-realtime-preview",
        tools=TOOLS,
        instructions=INSTRUCTIONS,
    )

    # Latency measurement starts
    start = time.perf_counter()

    # Step 1: Automatic Speech Recognition (stub call)
    # In a real pipeline, we call asr_provider.transcribe(audio_bytes)
    await asr_provider.transcribe(b"fake audio input")
    after_asr = time.perf_counter()

    # Step 2: LLM processing (agent.aconnect internally handles LLM + streaming)
    # await agent.aconnect(browser_receive_stream, websocket.send_text)
    # after_llm = time.perf_counter()
    
    # Skip LLM for now, just log a placeholder
    print("LLM processing skipped (test mode)")
    after_llm = time.perf_counter()

    # Step 3: Text-to-Speech synthesis (stub call)
    await tts_provider.synthesize("fake reply text")
    after_tts = time.perf_counter()

    # Print latency breakdown (to console for now, later Prometheus/Grafana)
    print("ASR latency:", after_asr - start, "seconds")
    print("LLM latency:", after_llm - after_asr, "seconds")
    print("TTS latency:", after_tts - after_llm, "seconds")
    # Latency measurement ends

# Twilio Voice Webhook (Media Stream + DTMF)
# Main Voice webhook (accepts both GET + POST for easier testing)
async def twilio_voice(request):
    print("✅ [/twilio/voice] Incoming request received (Media Stream mode)")
    print("   ↳ Method:", request.method)

    try:
        form = await request.form()
        print("   ↳ Form data:", dict(form))
    except Exception:
        print("   ↳ No form data (probably GET request)")

    resp = VoiceResponse()
    
    # Media Streams (Twilio will open a WSS to /twilio/stream)
    start = Start()
    wss_url = f"{PUBLIC_URL.replace('https://', 'wss://')}/twilio/stream"
    start.stream(url=wss_url)
    resp.append(start)
    
    # Greeting
    resp.say("You are now connected to the AI Voice Agent.", voice="alice", language="en-US")
    
    # Gather DTMF input
    gather = Gather(
        input="dtmf",
        num_digits=1,
        action=f"{PUBLIC_URL}/twilio/dtmf",
        method="POST",
        timeout=5,
    )
    gather.say("Press 1 to continue talking to the AI agent, or 2 to end the call.", voice="alice")
    resp.append(gather)

    print("   ↳ Responding with TwiML <Stream> + <Say> + <Gather>")
    return PlainTextResponse(str(resp), media_type="application/xml")

# Twilio DTMF handler
async def twilio_dtmf(request):
    form = await request.form()
    digit = form.get("Digits")
    print(f"[/twilio/dtmf] Digit pressed: {digit}")

    resp = VoiceResponse()

    if digit == "1":
        resp.say("You chose to continue with the AI agent.", voice="alice")

        # Re-attach Media Stream to keep audio flowing
        start = Start()
        wss_url = f"{PUBLIC_URL.replace('https://', 'wss://')}/twilio/stream"
        start.stream(url=wss_url)
        resp.append(start)

        # Add another Gather for next DTMF input
        gather = Gather(
            input="dtmf",
            num_digits=1,
            action=f"{PUBLIC_URL}/twilio/dtmf",
            method="POST",
            timeout=5,
        )
        gather.say("Press 1 to keep talking, or 2 to hang up.", voice="alice")
        resp.append(gather)

    elif digit == "2":
        resp.say("Goodbye!", voice="alice")
        resp.hangup()
    else:
        resp.say("Invalid input. Please try again.", voice="alice")

    return PlainTextResponse(str(resp), media_type="application/xml")

# Fallback handler (if the main webhook fails)
async def twilio_fallback(request):
    print("⚠️ [/twilio/fallback] Fallback handler triggered")  # Debug log
    print("   ↳ Method:", request.method)
    resp = VoiceResponse()
    resp.say("Sorry, our agent is unavailable. Please try again later.",
             voice="alice", language="en-US")
    return PlainTextResponse(str(resp), media_type="application/xml")

# Call status events (initiated, ringing, in-progress, completed)
async def twilio_status(request):
    form = await request.form()
    print("📞 [/twilio/status] Call status update:", dict(form))  # Debug log
    return PlainTextResponse("ok")

# Outbound call trigger API
async def callme(request):
    print("📞 [/callme] Triggering outbound call via Twilio")  # Debug log

    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )
    
    # Read config from .env
    my_number = os.getenv("MY_PHONE_NUMBER")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

    # Trigger outbound call
    call = client.calls.create(
        to=my_number,
        from_=twilio_number,
        url=f"{PUBLIC_URL}/twilio/voice"
    )

    return PlainTextResponse(f"✅ Call triggered, SID: {call.sid}")

# Twilio Media Stream WebSocket endpoint
# Receive μ-law audio frames from Twilio, decode to PCM16, and record to WAV file.
async def twilio_stream(websocket: WebSocket):
    await websocket.accept()
    print("🎧 Twilio Media Stream connected")

    wav_writer = None
    wav_path = None

    try:
        while True:
            try:
                message = await websocket.receive_json()
            except Exception as e:
                print("⚠️ JSON parse error:", e)
                continue

            event = message.get("event")

            if event == "start":
                # Use streamSid + timestamp as filename to avoid collisions
                stream_sid = message.get("start", {}).get("streamSid") or message.get("streamSid")
                ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
                filename = f"call-{ts}-{stream_sid}.wav" if stream_sid else f"call-{ts}.wav"
                wav_path = os.path.join(RECORDINGS_DIR, filename)

                # Open WAV writer (8kHz, mono, 16-bit)
                wav_writer = wave.open(wav_path, "wb")
                wav_writer.setnchannels(1)
                wav_writer.setsampwidth(2)     # 16-bit
                wav_writer.setframerate(8000)

                print(f"📁 Recording started → {wav_path}")
                print(f"📞 Call started: {message}")

            elif event == "media":
                if not wav_writer:
                    continue  # safety guard

                # Twilio sends base64-encoded μ-law @ 8kHz mono
                audio_payload = message["media"]["payload"]
                ulaw_bytes = base64.b64decode(audio_payload)

                # μ-law -> PCM16 (numpy array of int16)
                pcm_array = g711.decode_ulaw(ulaw_bytes)
                # Ensure dtype int16 then to raw bytes
                pcm_bytes = np.asarray(pcm_array, dtype=np.int16).tobytes()

                # Append raw PCM frames to WAV
                wav_writer.writeframes(pcm_bytes)

                print(f"🎤 Received audio chunk: ulaw={len(ulaw_bytes)} bytes, pcm={len(pcm_bytes)} bytes")

            elif event == "stop":
                print("🛑 Call ended (stop event)")
                break

    except Exception as e:
        print("⚠️ Twilio stream error:", e)
    finally:
        # Close the WAV file so header is finalized
        try:
            if wav_writer is not None:
                wav_writer.close()
                print(f"✅ Recording saved: {wav_path}")
        finally:
            await websocket.close()

# HTTP endpoint to download recordings
async def get_recording(request):
    filename = request.path_params["filename"]
    file_path = os.path.join(RECORDINGS_DIR, filename)
    if os.path.exists(file_path):
        print(f"⬇️ Downloading recording: {file_path}")
        return FileResponse(file_path, media_type="audio/wav", filename=filename)
    else:
        print(f"❌ Recording not found: {file_path}")
        return PlainTextResponse("Recording not found", status_code=404)
    
# Serve the homepage HTML file.
async def homepage(request):
    with open("src/server/static/index.html") as f:
        html = f.read()
        return HTMLResponse(html)

# Healthcheck
async def healthcheck(request):
    return HTMLResponse("OK - Voice Agent Server Running")

# Routes
routes = [
    Route("/", homepage),
    Route("/health", healthcheck),
    WebSocketRoute("/ws", websocket_endpoint),
    # Twilio endpoints (now accept GET + POST for /twilio/voice)
    Route("/callme", callme, methods=["GET"]),
    Route("/twilio/voice", twilio_voice, methods=["GET", "POST"]),
    Route("/twilio/dtmf", twilio_dtmf, methods=["POST"]),
    Route("/twilio/fallback", twilio_fallback, methods=["POST"]),
    Route("/twilio/status", twilio_status, methods=["POST"]),
    WebSocketRoute("/twilio/stream", twilio_stream),
    Route("/recordings/{filename}", get_recording, methods=["GET"]),
]

app = Starlette(debug=True, routes=routes)

# Serve static files (JS worklets etc.)
app.mount("/static", StaticFiles(directory="src/server/static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)