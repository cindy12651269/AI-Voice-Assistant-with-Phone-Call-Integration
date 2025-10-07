import "dotenv/config";
import { type WebSocket } from "ws";
import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { createNodeWebSocket } from "@hono/node-ws";
import { serveStatic } from "@hono/node-server/serve-static";

// LangChain voice agent (for AI voice logic)
import { OpenAIVoiceReactAgent } from "./lib/langchain_openai_voice";
import { INSTRUCTIONS } from "./prompt";
import { TOOLS } from "./tools";

// Twilio Voice SDK for browser softphone
import { Device } from "@twilio/voice-sdk";

// SIP.js for optional WebRTC softphone mode
import { UserAgent, Registerer, Inviter, URI } from "sip.js";

// 🚀 Setup Hono app + WebSocket upgrade (AI Realtime channel)
const app = new Hono();
const { injectWebSocket, upgradeWebSocket } = createNodeWebSocket({ app });

// 📄 Serve static demo UI
// Compatibility fix: some Hono versions prefer `root` + `path`
app.use("/", serveStatic({ root: "./static", path: "index.html" }));
app.use("/static/*", serveStatic({ root: "./" }));

// 🔊 WebSocket route for AI voice streaming (ASR → LLM → TTS)
app.get(
  "/ws",
  upgradeWebSocket(() => ({
    onOpen: async (evt: any, ws: any) => {
      if (!process.env.OPENAI_API_KEY) {
        console.error("❌ Missing OPENAI_API_KEY, closing WebSocket.");
        return ws.close();
      }

      // ✅ Handle missing evt.request (local dev)
      const url = evt.request
        ? new URL(evt.request.url)
        : new URL("http://localhost");

      const asrProvider = url.searchParams.get("asr") || "openai";
      const ttsProvider = url.searchParams.get("tts") || "openai";

      console.log(
        `Client connected with ASR=${asrProvider}, TTS=${ttsProvider}`
      );

      const agent = new OpenAIVoiceReactAgent({
        instructions: INSTRUCTIONS,
        tools: TOOLS,
        model: "gpt-4o-realtime-preview",
      });

      await agent.connect((ws.raw as any) as WebSocket, ws.send.bind(ws));
    },
    onClose: () => console.log("🔒 WebSocket closed"),
  }))
);

// ☎️ Twilio Voice SDK – Browser Softphone
async function initTwilioDevice() {
  try {
    // Read from .env (works in Node/Hono)
    const apiBase = process.env.PUBLIC_URL || "http://localhost:8000";

    // Step 1: Request a token from backend
    const resp = await fetch(`${apiBase}/twilio/token?identity=demo_user`);
    const { token } = await resp.json();

    // Step 2: Initialize Twilio Device
    const device = new Device(token);

    // Step 3: Event listeners
    device.on("ready", () => console.log("✅ Twilio Device ready"));
    device.on("error", (e) => console.error("❌ Twilio Error:", e));
    device.on("incoming", (call) => {
      console.log("📞 Incoming call from:", call.parameters.From);
      call.accept();
    });

    // Step 4: Global test helper
    (window as any).makeCall = (to: string) => {
      console.log(`📲 Dialing ${to}...`);
      device.connect({ params: { To: to } });
    };

    console.log("🎧 Twilio Voice SDK initialized successfully.");
  } catch (err) {
    console.error("❌ Twilio initialization failed:", err);
  }
}

// SIP.js – Alternative WebRTC Softphone (Mock-compatible)
async function initSIPClient() {
  try {
    // Use URI object (SIP.js type-safe)
    const uri = new URI("sip", "demo", "localhost");

    // Use mock local server (for demo only)
    const ua = new UserAgent({
      uri,
      transportOptions: { server: "wss://127.0.0.1:5060/ws" },
    });

    // Step 1: Start & register UserAgent
    const registerer = new Registerer(ua);
    await ua.start();
    await registerer.register();
    console.log("✅ SIP.js UserAgent started (mock mode)");

    // Step 2: Add global test helper
    (window as any).sipCall = async (target: string) => {
      const targetURI = new URI("sip", target, "localhost");
      const inviter = new Inviter(ua, targetURI);
      await inviter.invite();
      console.log(`📞 SIP call to ${target} started`);
    };
  } catch (err) {
    console.error("❌ SIP.js init error:", err);
  }
}

// Bootstrapping server
const port = 3000;
const server = serve({ fetch: app.fetch, port });
injectWebSocket(server);

console.log(`🚀 Frontend voice server running on port ${port}`);

// Auto-start Twilio for demo; SIP.js can be launched manually
initTwilioDevice();
// initSIPClient(); // Uncomment to test SIP softphone


