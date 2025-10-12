// SIP.js Softphone Client for Asterisk WebRTC
// Version: Bob

import { UserAgent, Registerer, Inviter, URI } from "./libs/sip.js";

window.addEventListener("DOMContentLoaded", async () => {
  console.log("🚀 Initializing SIP.js softphone for BOB...");


  // Configuration (Bob)
  const SIP_SERVER = "ws://localhost:8089/ws"; // For local testing (change to wss:// after SSL)
  const SIP_DOMAIN = "localhost";
  const SIP_USER = "bob";
  const SIP_PASS = "1234";

  // Create SIP URI and UserAgent
  const uri = new URI("sip", SIP_USER, SIP_DOMAIN);
  const ua = new UserAgent({
    uri,
    authorizationUsername: SIP_USER,
    authorizationPassword: SIP_PASS,
    transportOptions: { server: SIP_SERVER },
  });

  const registerer = new Registerer(ua);

  // Handle incoming calls
  ua.delegate = {
    onInvite(invitation) {
      console.log("📞 Incoming SIP call to BOB!");
      invitation.accept()
        .then(() => console.log("✅ Bob accepted the call."))
        .catch((err) => console.error("❌ Error accepting call:", err));
    },
  };

  // Connect and register
  try {
    await ua.start();
    await registerer.register();
    console.log(`✅ SIP.js softphone registered as ${SIP_USER}@${SIP_DOMAIN}`);
  } catch (err) {
    console.error("❌ Failed to start or register SIP.js (BOB):", err);
  }

  // Manual calling function
  window.makeCall = async (target) => {
    try {
      const targetURI = new URI("sip", target, SIP_DOMAIN);
      const inviter = new Inviter(ua, targetURI);
      await inviter.invite();
      console.log(`📲 Bob calling ${target} via SIP...`);
    } catch (err) {
      console.error("❌ Bob call failed:", err);
    }
  };

  console.log("✅ SIP.js softphone (BOB) ready. Try: makeCall('alice')");
});
