from dotenv import load_dotenv
load_dotenv()

import os
import time
import uvicorn
import base64
import wave
from datetime import datetime
import numpy as np          # for PCM16 buffer handling
import g711                 # g711: μ-law <-> PCM helpers

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
from twilio.twiml.voice_response import VoiceResponse
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

# Twilio Voice Webhook (Connect<Stream> + Say tips; NO <Gather>) 
# To open a bidirectional Media Stream, DTMF events will be delivered over the same WebSocket as JSON (event='dtmf').
async def twilio_voice(request):
    print("✅ [/twilio/voice] Incoming request (Connect<Stream> mode)")
    print("   ↳ Method:", request.method)

    # Twilio typically POSTs form data. Log it if available (debugging aid).
    try:
        form = await request.form()
        form_dict = dict(form)
        print("   ↳ Form data keys:", list(form_dict.keys()))
    except Exception:
        print("   ↳ No form data (likely GET test from browser)")

    resp = VoiceResponse()

    # Build WSS URL from PUBLIC_URL
    wss_url = f"{PUBLIC_URL.replace('https://', 'wss://')}/twilio/stream"

    # Use <Connect><Stream> (keeps media flowing; DTMF delivered as JSON events)
    with resp.connect() as connect:
        connect.stream(url=wss_url)

    # Optional voice prompts (No <Gather> to avoid pausing the stream)
    resp.say("You are now connected to the AI Voice Agent.", voice="alice", language="en-US")
    resp.say("Press 1 to continue talking, or 2 to hang up.", voice="alice", language="en-US")

    print("   ↳ Responding with TwiML <Connect><Stream> + <Say> prompts")
    return PlainTextResponse(str(resp), media_type="application/xml")

# Fallback handler (if the main webhook fails)
async def twilio_fallback(request):
    print("⚠️ [/twilio/fallback] Fallback handler triggered")  # Debug log
    print("   ↳ Method:", request.method)
    resp = VoiceResponse()
    resp.say("Sorry, our agent is unavailable. Please try again later.",
             voice="alice", language="en-US")
    return PlainTextResponse(str(resp), media_type="application/xml")

# Call status events (initiated, ringing, in-progress, completed) for analytics/debugging
async def twilio_status(request):
    try:
        form = await request.form()
        print("📞 [/twilio/status] Call status:", dict(form))
    except Exception as e:
        print("📞 [/twilio/status] No form; err:", e)
    return PlainTextResponse("ok")

# Outbound call trigger API
# Twilio will fetch TwiML from /twilio/voice, which opens the media stream.
async def callme(request):
    print("📞 [/callme] Triggering outbound call via Twilio")  # Debug log

    client = Client(
        os.getenv("TWILIO_ACCOUNT_SID"),
        os.getenv("TWILIO_AUTH_TOKEN")
    )
    
    # Read config from .env
    my_number = os.getenv("MY_PHONE_NUMBER")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")
    
    if not my_number or not twilio_number:
        return PlainTextResponse("Missing MY_PHONE_NUMBER or TWILIO_PHONE_NUMBER", status_code=500)
    
    # Trigger outbound call
    call = client.calls.create(
        to=my_number,
        from_=twilio_number,
        url=f"{PUBLIC_URL}/twilio/voice"
    )
    print(f"   ↳ Outbound Call SID: {call.sid}")
    return PlainTextResponse(f"✅ Call triggered, SID: {call.sid}")

# Twilio Media Stream WebSocket endpoint
# Receive μ-law audio frames from Twilio, decode to PCM16, and record to WAV file.
async def twilio_stream(websocket: WebSocket):
    await websocket.accept()
    print("🎧 Twilio Media Stream connected")

    wav_writer = None
    wav_path = None
    total_media_msgs = 0

    try:
        while True:
            # Receive next JSON frame
            try:
                message = await websocket.receive_json()
            except Exception as e:
                print("⚠️ JSON parse error (non-JSON frame?):", e)
                continue

            event = message.get("event")

            if event == "start":
                start_info = message.get("start", {})
                stream_sid = start_info.get("streamSid") or message.get("streamSid")
                sample_rate = start_info.get("mediaFormat", {}).get("sampleRate", 8000)
                encoding = start_info.get("mediaFormat", {}).get("encoding")

                # Generate a unique filename per stream
                ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
                filename = f"call-{ts}-{stream_sid}.wav" if stream_sid else f"call-{ts}.wav"
                wav_path = os.path.join(RECORDINGS_DIR, filename)

                # Open WAV writer: mono, 16-bit, 8kHz
                wav_writer = wave.open(wav_path, "wb")
                wav_writer.setnchannels(1)
                wav_writer.setsampwidth(2)
                wav_writer.setframerate(int(sample_rate))

                print(f"📁 Recording started → {wav_path}")
                print(f"📞 Call metadata: streamSid={stream_sid}, encoding={encoding}, sr={sample_rate}")

            elif event == "media":
                # Ensure we started recording
                if not wav_writer:
                    print("⚠️ Received media before 'start'; ignoring chunk")
                    continue

                # Twilio sends base64 μ-law (20ms per frame; typically 160 bytes)
                payload_b64 = message.get("media", {}).get("payload")
                if not payload_b64:
                    print("⚠️ Empty media payload")
                    continue

                ulaw_bytes = base64.b64decode(payload_b64)
                if not ulaw_bytes:
                    print("⚠️ media payload base64-decoded to empty bytes")
                    continue

                # μ-law → PCM16 (numpy array of int16)
                try:
                    pcm_array = g711.decode_ulaw(ulaw_bytes)
                except Exception as e:
                    print("❌ μ-law decode failed:", e)
                    continue

                pcm_bytes = np.asarray(pcm_array, dtype=np.int16).tobytes()

                # Append raw PCM frames
                wav_writer.writeframes(pcm_bytes)
                total_media_msgs += 1

                # Debug: first few chunks print more details, afterwards compact
                if total_media_msgs <= 10:
                    print(f"🎤 Media chunk #{total_media_msgs}: ulaw={len(ulaw_bytes)}B, pcm={len(pcm_bytes)}B")
                elif total_media_msgs % 100 == 0:
                    print(f"… received {total_media_msgs} media chunks so far")

            elif event == "dtmf":
                # Twilio delivers DTMF without breaking the stream when using <Connect><Stream>
                digit = message.get("dtmf", {}).get("digit")
                dur = message.get("dtmf", {}).get("duration")
                print(f"🎹 DTMF received: digit={digit}, duration={dur}ms (stream continues)")

            elif event == "stop":
                print(f"🛑 Stop event received. Total media chunks = {total_media_msgs}")
                break

            else:
                print(f"ℹ️ Unknown event '{event}': {message}")

    except Exception as e:
        print("⚠️ Twilio stream error:", e)

    finally:
        try:
            if wav_writer:
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
    
    # Twilio flows
    Route("/twilio/voice", twilio_voice, methods=["GET", "POST"]), # Now accept GET + POST for /twilio/voice
    Route("/twilio/status", twilio_status, methods=["POST"]),
    WebSocketRoute("/twilio/stream", twilio_stream),

    # Outbound trigger
    Route("/callme", callme, methods=["GET"]),

    # Recording download
    Route("/recordings/{filename}", get_recording, methods=["GET"]),
]

app = Starlette(debug=True, routes=routes)

# Serve static files (JS worklets etc.)
app.mount("/static", StaticFiles(directory="src/server/static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)