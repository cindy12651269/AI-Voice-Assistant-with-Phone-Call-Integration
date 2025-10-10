import { UserAgent, Registerer, Inviter, URI } from "sip.js";

window.addEventListener("DOMContentLoaded", async () => {
  console.log("🚀 Initializing SIP.js softphone...");

  // Replace with your Asterisk server IP or domain
  const SIP_SERVER = "wss://localhost:8089/ws"; // WebSocket over TLS
  const SIP_DOMAIN = "example.com";
  const SIP_USER = "alice";
  const SIP_PASS = "1234";

  // Define SIP URI and options
  const uri = new URI("sip", SIP_USER, SIP_DOMAIN);
  const ua = new UserAgent({
    uri,
    authorizationUsername: SIP_USER,
    authorizationPassword: SIP_PASS,
    transportOptions: { server: SIP_SERVER },
  });

  const registerer = new Registerer(ua);

  ua.delegate = {
    onInvite(invitation) {
      console.log("📞 Incoming call!");
      invitation.accept();
    },
  };

  await ua.start();
  await registerer.register();

  // For browser console manual testing
  window.makeCall = async (target) => {
    const targetURI = new URI("sip", target, SIP_DOMAIN);
    const inviter = new Inviter(ua, targetURI);
    await inviter.invite();
    console.log(`📲 Calling ${target} via SIP...`);
  };

  console.log("✅ SIP.js softphone ready. Try: makeCall('bob')");
});
