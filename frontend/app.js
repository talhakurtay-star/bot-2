// Jarvis - tarayıcı tarafı: ses tanıma (STT), seslendirme (TTS), wake word, sohbet.

const API = ""; // aynı sunucudan servis edildiği için boş
const SESSION_ID = "web-" + (localStorage.getItem("jarvis_sid") || Math.random().toString(36).slice(2));
localStorage.setItem("jarvis_sid", SESSION_ID.replace("web-", ""));

const WAKE_WORD = "jarvis";

const el = {
  status: document.getElementById("status"),
  orb: document.getElementById("orb"),
  chat: document.getElementById("chat"),
  input: document.getElementById("textInput"),
  send: document.getElementById("sendBtn"),
  mic: document.getElementById("micBtn"),
  wake: document.getElementById("wakeBtn"),
  tts: document.getElementById("ttsToggle"),
  reset: document.getElementById("resetBtn"),
};

let wakeMode = false;     // sürekli wake word dinleme açık mı
let recognizing = false;  // şu an dinliyor mu
let busy = false;         // istek işleniyor mu

// ---- Yardımcılar ----
function setStatus(text) { el.status.textContent = text; }
function setOrb(state) { el.orb.className = "orb " + state; }

function addMessage(role, text) {
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.textContent = text;
  el.chat.appendChild(div);
  el.chat.scrollTop = el.chat.scrollHeight;
}

// ---- Seslendirme (TTS) ----
function speak(text) {
  if (!el.tts.checked || !("speechSynthesis" in window)) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "tr-TR";
  u.rate = 1.05;
  const trVoice = speechSynthesis.getVoices().find(v => v.lang.startsWith("tr"));
  if (trVoice) u.voice = trVoice;
  u.onstart = () => setOrb("speaking");
  u.onend = () => { setOrb(wakeMode ? "listening" : "idle"); };
  speechSynthesis.speak(u);
}

// ---- Sunucuya mesaj gönder ----
async function sendToBrain(text) {
  if (!text.trim() || busy) return;
  busy = true;
  addMessage("user", text);
  setStatus("Düşünüyorum...");
  setOrb("thinking");
  try {
    const res = await fetch(API + "/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text, session_id: SESSION_ID }),
    });
    const data = await res.json();
    addMessage("assistant", data.reply);
    setStatus("Hazır");
    speak(data.reply);
  } catch (e) {
    addMessage("assistant", "Sunucuya bağlanamadım. Backend çalışıyor mu?");
    setStatus("Bağlantı hatası");
  } finally {
    busy = false;
    if (!el.tts.checked) setOrb(wakeMode ? "listening" : "idle");
  }
}

// ---- Ses tanıma (STT) ----
const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
let recognition = null;

if (SR) {
  recognition = new SR();
  recognition.lang = "tr-TR";
  recognition.continuous = false;
  recognition.interimResults = false;

  recognition.onstart = () => { recognizing = true; setOrb("listening"); };
  recognition.onend = () => {
    recognizing = false;
    el.mic.classList.remove("active");
    // Wake modu açıksa tekrar dinlemeye başla
    if (wakeMode && !busy) {
      setTimeout(() => { try { recognition.start(); } catch (e) {} }, 250);
    } else {
      setOrb("idle");
    }
  };
  recognition.onerror = (e) => {
    if (e.error === "no-speech" || e.error === "aborted") return;
    setStatus("Mikrofon hatası: " + e.error);
  };
  recognition.onresult = (event) => {
    const transcript = event.results[0][0].transcript.trim();
    if (!transcript) return;

    if (wakeMode) {
      const lower = transcript.toLowerCase();
      if (lower.includes(WAKE_WORD)) {
        // "jarvis" kelimesinden sonrasını komut olarak al
        const after = lower.split(WAKE_WORD).slice(1).join(WAKE_WORD).trim();
        const command = after || transcript.replace(new RegExp(WAKE_WORD, "i"), "").trim();
        if (command) {
          sendToBrain(command);
        } else {
          setStatus("Efendim?");
          speak("Efendim?");
        }
      } else {
        setStatus("'Jarvis' bekleniyor...");
      }
    } else {
      sendToBrain(transcript);
    }
  };
} else {
  setStatus("Tarayıcınız ses tanımayı desteklemiyor (Chrome önerilir).");
  el.mic.disabled = true;
  el.wake.disabled = true;
}

// ---- Tek seferlik mikrofon ----
el.mic.addEventListener("click", () => {
  if (!recognition) return;
  if (recognizing) {
    recognition.stop();
    el.mic.classList.remove("active");
  } else {
    wakeMode = false;
    updateWakeButton();
    el.mic.classList.add("active");
    setStatus("Dinliyorum...");
    try { recognition.start(); } catch (e) {}
  }
});

// ---- Wake word modu ----
function updateWakeButton() {
  el.wake.textContent = "Jarvis'i dinle: " + (wakeMode ? "Açık" : "Kapalı");
  el.wake.className = wakeMode ? "wake-on" : "wake-off";
}

el.wake.addEventListener("click", () => {
  if (!recognition) return;
  wakeMode = !wakeMode;
  updateWakeButton();
  if (wakeMode) {
    setStatus("'Jarvis' bekleniyor...");
    try { recognition.start(); } catch (e) {}
  } else {
    recognition.stop();
    setStatus("Hazır");
    setOrb("idle");
  }
});

// ---- Yazılı giriş ----
el.send.addEventListener("click", () => {
  const t = el.input.value;
  el.input.value = "";
  sendToBrain(t);
});
el.input.addEventListener("keydown", (e) => {
  if (e.key === "Enter") { el.send.click(); }
});

// ---- Hafıza temizleme ----
el.reset.addEventListener("click", async () => {
  await fetch(API + "/reset", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: "", session_id: SESSION_ID }),
  });
  el.chat.innerHTML = "";
  addMessage("assistant", "Hafıza temizlendi efendim.");
});

// Sesleri önceden yükle (Chrome bazen geç yüklüyor)
if ("speechSynthesis" in window) {
  speechSynthesis.onvoiceschanged = () => {};
}

// Açılış
addMessage("assistant", "Merhaba efendim. Size nasıl yardımcı olabilirim? Yazabilir, mikrofona basabilir veya 'Jarvis' diyerek beni çağırabilirsiniz.");
setOrb("idle");
