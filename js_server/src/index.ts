import "dotenv/config";
import { type WebSocket } from "ws";
import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { createNodeWebSocket } from "@hono/node-ws";
import { serveStatic } from "@hono/node-server/serve-static";
import path from "path";

// LangChain voice agent (for AI voice logic)
import { OpenAIVoiceReactAgent } from "./lib/langchain_openai_voice";
import { INSTRUCTIONS } from "./prompt";
import { TOOLS } from "./tools";


// 1) App initialization
const app = new Hono();
const { injectWebSocket, upgradeWebSocket } = createNodeWebSocket({ app });

// 🐛 DEBUG
console.log("🔧 process.cwd() =", process.cwd());
console.log("🔧 __dirname =", __dirname);

// 2) Security: CSP header (allow esm.sh for SIP.js)
const isDev = process.env.NODE_ENV !== "production";

app.use("*", async (c, next) => {
  const cspHeader = isDev
    ? [
        // Development: allow SIP.js & WebRTC sources
        "default-src 'self' data: blob:;",
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://esm.sh https://unpkg.com;",
        "connect-src * ws://localhost:8089 wss://localhost:8089;",
        "style-src 'self' 'unsafe-inline';",
      ].join(" ")
    : [
        // Production: tighten security
        "default-src 'self' data: blob:;",
        "script-src 'self';",
        "connect-src 'self';",
        "style-src 'self';",
      ].join(" ");

  c.header("Content-Security-Policy", cspHeader);
  await next();
});

// 3) Serve static frontend files
const staticDir = path.resolve(process.cwd(), "static");
console.log("📂 Serving static files from:", staticDir);

app.use("/", serveStatic({ root: staticDir, path: "index.html" }));

app.use(
  "/static/*",
  serveStatic({
    root: staticDir,
    rewriteRequestPath: (reqPath) => {
      const rewritten = reqPath.replace(/^\/static/, "");
      console.log("📄 Static request:", reqPath, "→", rewritten); // 🐛 DEBUG
      return rewritten;
    },
  })
);

app.use("/index-bob.html", serveStatic({ root: staticDir, path: "index-bob.html" }));

// 4) WebSocket route for AI voice streaming (ASR → LLM → TTS)
app.get(
  "/ws",
  upgradeWebSocket(() => ({
    onOpen: async (evt: any, ws: any) => {
      if (!process.env.OPENAI_API_KEY) {
        console.error("❌ Missing OPENAI_API_KEY, closing WebSocket.");
        return ws.close();
      }

      const url = evt.request
        ? new URL(evt.request.url)
        : new URL("http://localhost");
      const asrProvider = url.searchParams.get("asr") || "openai";
      const ttsProvider = url.searchParams.get("tts") || "openai";
      console.log(`🔗 WebSocket connected (ASR=${asrProvider}, TTS=${ttsProvider})`);

      const agent = new OpenAIVoiceReactAgent({
        instructions: INSTRUCTIONS,
        tools: TOOLS,
        model: "gpt-4o-realtime-preview",
      });

      await agent.connect((ws.raw as any as WebSocket), ws.send.bind(ws));
    },
    onClose: () => console.log("🔒 WebSocket closed"),
  }))
);

// 5) Start server
const port = 3000;
const server = serve({ fetch: app.fetch, port });
injectWebSocket(server);

console.log(`🚀 Frontend voice server running on port ${port}`);

