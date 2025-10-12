// SIP.js Softphone Client for Asterisk WebRTC

// This script connects to a local Asterisk server via WebSocket (PJSIP + WebRTC).
// Allows browser-based SIP registration and call initiation (SIP-to-SIP).
// Tested with Docker container running Asterisk + PJSIP on port 8089.

// Chrome/Edge only allow secure WebSocket (wss://) by default.
// For local testing, please temporarily use ws://localhost:8089/ws.

import { UserAgent, Registerer, Inviter, URI } from "./libs/sip.js";


window.addEventListener("DOMContentLoaded", async () => {
  console.log("🚀 Initializing SIP.js softphone...");

  // Configuration (adjust here)
  const SIP_SERVER = "ws://localhost:8089/ws"; // Use "wss://" after SSL setup
  const SIP_DOMAIN = "localhost";              // Your Asterisk host (same as docker host)
  const SIP_USER = "alice";                    // Default SIP user
  const SIP_PASS = "1234";                     // Default password


  // Create SIP URI and UserAgent
  const uri = new URI("sip", SIP_USER, SIP_DOMAIN);
  const ua = new UserAgent({
    uri,
    authorizationUsername: SIP_USER,
    authorizationPassword: SIP_PASS,
    transportOptions: { server: SIP_SERVER },
  });

  // Create SIP Registerer (to register this user)
  const registerer = new Registerer(ua);

  // Handle incoming calls
  ua.delegate = {
    onInvite(invitation) {
      console.log("📞 Incoming SIP call detected!");
      invitation.accept()
        .then(() => console.log("✅ Call accepted."))
        .catch((err) => console.error("❌ Error accepting call:", err));
    },
  };

  // Connect and register
  try {
    await ua.start();
    await registerer.register();
    console.log(`✅ SIP.js softphone registered as ${SIP_USER}@${SIP_DOMAIN}`);
  } catch (err) {
    console.error("❌ Failed to start or register SIP.js:", err);
  }

  // Manual calling function
  window.makeCall = async (target) => {
    try {
      const targetURI = new URI("sip", target, SIP_DOMAIN);
      const inviter = new Inviter(ua, targetURI);
      await inviter.invite();
      console.log(`📲 Calling ${target} via SIP...`);
    } catch (err) {
      console.error("❌ Call failed:", err);
    }
  };

  // Ready message
  console.log("✅ SIP.js softphone ready. Try in console: makeCall('bob')");
});

