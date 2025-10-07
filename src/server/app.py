import sys, os
sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

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
import requests             # for downloading Twilio recordings

from starlette.applications import Starlette
from starlette.responses import HTMLResponse, PlainTextResponse
from starlette.routing import Route, WebSocketRoute
from starlette.staticfiles import StaticFiles
from starlette.websockets import WebSocket
from starlette.responses import FileResponse, JSONResponse

from langchain_openai_voice import OpenAIVoiceReactAgent
from server.utils import websocket_stream
from server.prompt import INSTRUCTIONS
from server.tools import TOOLS

# Import provider factories from utils.py 
from langchain_openai_voice.utils import get_asr_provider, get_tts_provider

# Import Twilio VoiceResponse to generate TwiML
from twilio.twiml.voice_response import VoiceResponse, Dial, Number
from twilio.rest import Client

# For Twilio token endpoint
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant

# PUBLIC_URL (must include https:// in .env)
PUBLIC_URL = os.getenv("PUBLIC_URL")
if not PUBLIC_URL:
    raise ValueError("PUBLIC_URL is not set. Please add it to your .env (e.g. https://your-service.onrender.com)")

# Twilio credentials (for downloading recordings)
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")

# Directory for server-side recordings (ephemeral on Render; persists until redeploy)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RECORDINGS_DIR = os.path.join(BASE_DIR, "recordings")
os.makedirs(RECORDINGS_DIR, exist_ok=True) # Create if not exists

# Twilio Access Token endpoint 
async def twilio_token(request):
    account_sid = os.getenv("TWILIO_ACCOUNT_SID")
    api_key_sid = os.getenv("TWILIO_API_KEY_SID")
    api_key_secret = os.getenv("TWILIO_API_KEY_SECRET")
    twiml_app_sid = os.getenv("TWIML_APP_SID")
    identity = request.query_params.get("identity", "demo_user")

    token = AccessToken(account_sid, api_key_sid, api_key_secret, identity=identity)
    voice_grant = VoiceGrant(outgoing_application_sid=twiml_app_sid)
    token.add_grant(voice_grant)

    return JSONResponse({"token": token.to_jwt().decode("utf-8")})

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

# Twilio inbound/outbound call (AI Stream)
async def twilio_voice(request):
    print("✅ [/twilio/voice] Incoming request")

    resp = VoiceResponse()
    resp.say("You are now connected to the AI Voice Agent.", voice="alice", language="en-US")
    resp.say("Press 1 to continue talking, or 2 to hang up.", voice="alice", language="en-US")

    # Media Stream
    wss_url = f"{PUBLIC_URL.replace('https://', 'wss://')}/twilio/stream"
    with resp.connect() as connect:
        connect.stream(url=wss_url)

    twiml_str = str(resp)
    print("🔍 TwiML sent (AI Voice Agent):\n", twiml_str)
    return PlainTextResponse(twiml_str, media_type="application/xml")

# Twilio Media Stream WebSocket endpoint
async def twilio_stream(websocket: WebSocket):
    await websocket.accept()
    print("🎧 Twilio Media Stream connected")

    agent = OpenAIVoiceReactAgent(
        model="gpt-4o-realtime-preview",
        tools=TOOLS,
        instructions=INSTRUCTIONS,
    )

    wav_writer = None
    total_media_msgs = 0

    try:
        while True:
            try:
                message = await websocket.receive_json()
            except Exception as e:
                print("⚠️ JSON parse error:", e)
                continue

            event = message.get("event")

            if event == "start":
                sid = message["start"].get("streamSid")
                ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
                filename = f"call-{ts}-{sid}.wav"
                wav_path = os.path.join(RECORDINGS_DIR, filename)

                wav_writer = wave.open(wav_path, "wb")
                wav_writer.setnchannels(1)
                wav_writer.setsampwidth(2)
                wav_writer.setframerate(8000)
                print(f"📁 Recording started → {wav_path}")

            elif event == "media":
                if not wav_writer:
                    continue
                ulaw_bytes = base64.b64decode(message["media"]["payload"])
                pcm_array = g711.decode_ulaw(ulaw_bytes)
                pcm_bytes = np.asarray(pcm_array, dtype=np.int16).tobytes()
                wav_writer.writeframes(pcm_bytes)

                # Pass PCM bytes to the agent's audio handler 
                if hasattr(agent, "handleExternalAudioChunk"):
                    try:
                        await agent.handleExternalAudioChunk(pcm_bytes)
                    except Exception as e:
                        print("⚠️ Agent audio handler error:", e)

                total_media_msgs += 1
                if total_media_msgs <= 5:
                    print(f"🎤 Received media chunk #{total_media_msgs}")

            elif event == "dtmf":
                print(f"🎹 DTMF received: {message.get('dtmf')}")

            elif event == "stop":
                print("🛑 Stop event received")
                break

    finally:
        if wav_writer:
            wav_writer.close()
            print(f"✅ Recording saved.")
        await websocket.close()

# Twilio Call Status callback 
async def twilio_status(request):
    try:
        form = await request.form()
        data = dict(form)
    except Exception as e:
        data = {"_parse_error": str(e)}
    print("📞 [/twilio/status] Call status:", data)
    return PlainTextResponse("ok")

# Fallback handler (if the main webhook fails)
async def twilio_fallback(request):
    print("⚠️ [/twilio/fallback] Fallback handler triggered")  # Debug log
    print("   ↳ Method:", request.method)
    resp = VoiceResponse()
    resp.say("Sorry, our agent is unavailable. Please try again later.",
             voice="alice", language="en-US")
    return PlainTextResponse(str(resp), media_type="application/xml")

# Outbound call trigger API
# Twilio will fetch TwiML from /twilio/voice, which opens the media stream.
async def callme(request):
    print("📞 [/callme] Triggering outbound call via Twilio")

    client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    my_number = os.getenv("MY_PHONE_NUMBER")
    twilio_number = os.getenv("TWILIO_PHONE_NUMBER")

    if not my_number or not twilio_number:
        return PlainTextResponse("Missing MY_PHONE_NUMBER or TWILIO_PHONE_NUMBER", status_code=500)

    call = client.calls.create(
        to=my_number,
        from_=twilio_number,
        url=f"{PUBLIC_URL}/twilio/voice"
    )
    print(f"   ↳ Outbound Call SID: {call.sid}")
    return PlainTextResponse(f"✅ Call triggered, SID: {call.sid}")

# Download Local Recordings (debug only) 
async def get_recording(request):
    filename = request.path_params["filename"]
    file_path = os.path.join(RECORDINGS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg", filename=filename)
    else:
        return PlainTextResponse("Recording not found", status_code=404)
    
# Serve the homepage HTML file.
async def homepage(request):
    with open("server/static/index.html") as f:
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
    Route("/twilio/token", twilio_token, methods=["GET"]),
    Route("/twilio/voice", twilio_voice, methods=["GET", "POST"]), # Now accept GET + POST for /twilio/voice
    WebSocketRoute("/twilio/stream", twilio_stream),
    Route("/twilio/status", twilio_status, methods=["POST"]), 
    Route("/twilio/fallback", twilio_fallback, methods=["POST"]),
    
    # Outbound trigger
    Route("/callme", callme, methods=["GET"]),

    # Recording download
    Route("/recordings/{filename}", get_recording, methods=["GET"]),
]

app = Starlette(debug=True, routes=routes)

# Serve static files (JS worklets etc.)
app.mount("/static", StaticFiles(directory="server/static"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)