import "dotenv/config";
import { type WebSocket } from "ws";

import { serve } from "@hono/node-server";
import { Hono } from "hono";
import { createNodeWebSocket } from "@hono/node-ws";
import { serveStatic } from "@hono/node-server/serve-static";

import { OpenAIVoiceReactAgent } from "./lib/langchain_openai_voice";
import { INSTRUCTIONS } from "./prompt";
import { TOOLS } from "./tools";

const app = new Hono();

const { injectWebSocket, upgradeWebSocket } = createNodeWebSocket({ app });

// Serve static HTML for demo UI
app.use("/", serveStatic({ path: "./static/index.html" }));
app.use("/static/*", serveStatic({ root: "./" }));

// WebSocket route
app.get(
  "/ws",
  upgradeWebSocket(() => ({
    onOpen: async (evt: any, ws: any) => {
      if (!process.env.OPENAI_API_KEY) {
        return ws.close();
      }

      // ✅ Minimal fix: handle undefined evt.request
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
    onClose: () => {
      console.log("CLOSING");
    },
  }))
);

const port = 3000;

const server = serve({
  fetch: app.fetch,
  port,
});

injectWebSocket(server);

console.log(`Server is running on port ${port}`);

