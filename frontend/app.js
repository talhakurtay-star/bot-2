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
  voice: document.getElementById("voiceSelect"),
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
  // ```dil ... ``` bloklarını kod paneli olarak göster
  const parts = text.split(/```/);
  parts.forEach((part, i) => {
    if (i % 2 === 1) {
      const pre = document.createElement("pre");
      const lines = part.split("\n");
      const lang = lines[0].trim();
      const code = (lang && !lang.includes(" ")) ? lines.slice(1).join("\n") : part;
      if (lang && !lang.includes(" ")) {
        const tag = document.createElement("span");
        tag.className = "lang";
        tag.textContent = lang;
        pre.appendChild(tag);
      }
      pre.appendChild(document.createTextNode(code));
      div.appendChild(pre);
    } else if (part) {
      const span = document.createElement("span");
      span.textContent = part;
      div.appendChild(span);
    }
  });
  el.chat.appendChild(div);
  el.chat.scrollTop = el.chat.scrollHeight;
}

// Sesli okuma için kod bloklarını çıkar
function stripCode(text) {
  return text.replace(/```[\s\S]*?```/g, " (kodu ekranda gösterdim) ").trim();
}

// ---- Seslendirme (TTS) ----
function speak(text) {
  if (!el.tts.checked || !("speechSynthesis" in window)) return;
  const spoken = stripCode(text);
  if (!spoken) return;
  speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(spoken);
  u.lang = "tr-TR";
  u.rate = 1.05;
  const voices = speechSynthesis.getVoices();
  const chosen = el.voice && el.voice.value
    ? voices.find(v => v.name === el.voice.value)
    : voices.find(v => v.lang.startsWith("tr"));
  if (chosen) u.voice = chosen;
  u.onstart = () => setOrb("speaking");
  u.onend = () => { setOrb(wakeMode ? "listening" : "idle"); };
  speechSynthesis.speak(u);
}

// Ses listesini doldur (Türkçe sesler üstte)
function populateVoices() {
  if (!el.voice || !("speechSynthesis" in window)) return;
  const voices = speechSynthesis.getVoices();
  if (!voices.length) return;
  const tr = voices.filter(v => v.lang.startsWith("tr"));
  const others = voices.filter(v => !v.lang.startsWith("tr"));
  el.voice.innerHTML = "";
  [...tr, ...others].forEach(v => {
    const opt = document.createElement("option");
    opt.value = v.name;
    opt.textContent = `${v.name} (${v.lang})`;
    el.voice.appendChild(opt);
  });
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
  populateVoices();
  speechSynthesis.onvoiceschanged = populateVoices;
}

// ---- Hatırlatıcı bildirimleri (periyodik kontrol) ----
async function checkReminders() {
  try {
    const res = await fetch(API + "/reminders/due");
    const data = await res.json();
    for (const r of data.due || []) {
      const text = "⏰ Hatırlatma: " + r.text;
      addMessage("assistant", text);
      speak(text);
    }
  } catch (e) {
    // sunucu kapalıysa sessizce geç
  }
}
setInterval(checkReminders, 15000); // her 15 saniyede bir

// Açılış
addMessage("assistant", "Merhaba efendim. Size nasıl yardımcı olabilirim? Yazabilir, mikrofona basabilir veya 'Jarvis' diyerek beni çağırabilirsiniz.");
setOrb("idle");
