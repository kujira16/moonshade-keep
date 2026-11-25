// ゲームボーイ風の矩形波サウンド（WebAudio、曲もすべてオリジナル）
(function () {
  let ac = null, master = null, muted = localStorage.getItem("mk_mute") === "1";
  let bgm = null, nextTime = 0, step = 0, timer = null;

  function ensure() {
    if (!ac) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (!AC) return false;
      ac = new AC();
      master = ac.createGain();
      master.gain.value = muted ? 0 : 0.18;
      master.connect(ac.destination);
    }
    if (ac.state === "suspended") ac.resume();
    return true;
  }

  function tone(freq, t, dur, type = "square", vol = 0.5, slide = 0) {
    const o = ac.createOscillator(), g = ac.createGain();
    o.type = type;
    o.frequency.setValueAtTime(freq, t);
    if (slide) o.frequency.exponentialRampToValueAtTime(Math.max(30, freq * slide), t + dur);
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    o.connect(g); g.connect(master);
    o.start(t); o.stop(t + dur + 0.02);
  }
  let noiseBuf = null;
  function noise(t, dur, vol = 0.5) {
    if (!noiseBuf) {
      noiseBuf = ac.createBuffer(1, ac.sampleRate * 0.5, ac.sampleRate);
      const d = noiseBuf.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    }
    const s = ac.createBufferSource(), g = ac.createGain();
    s.buffer = noiseBuf;
    g.gain.setValueAtTime(vol, t);
    g.gain.exponentialRampToValueAtTime(0.001, t + dur);
    s.connect(g); g.connect(master);
    s.start(t); s.stop(t + dur);
  }

  const SFX = {
    jump: (t) => tone(220, t, 0.12, "square", 0.3, 2.2),
    whip: (t) => { noise(t, 0.08, 0.3); tone(900, t, 0.08, "square", 0.15, 0.4); },
    hit: (t) => { tone(160, t, 0.1, "square", 0.4, 0.5); noise(t, 0.06, 0.3); },
    hurt: (t) => tone(400, t, 0.3, "square", 0.4, 0.25),
    candle: (t) => { noise(t, 0.12, 0.35); tone(600, t, 0.1, "triangle", 0.3, 0.5); },
    pickup: (t) => { tone(660, t, 0.06, "square", 0.3); tone(990, t + 0.06, 0.1, "square", 0.3); },
    boss: (t) => { tone(80, t, 0.25, "square", 0.5, 0.5); noise(t, 0.2, 0.4); },
    explode: (t) => { noise(t, 0.6, 0.6); tone(120, t, 0.6, "square", 0.4, 0.2); },
    clear: (t) => [523, 659, 784, 1046].forEach((f, i) => tone(f, t + i * 0.12, 0.25, "square", 0.3)),
    die: (t) => [440, 370, 311, 262, 196].forEach((f, i) => tone(f, t + i * 0.12, 0.2, "square", 0.3)),
    select: (t) => tone(880, t, 0.08, "square", 0.25),
  };

  // 曲データ：音名(半音, 0=A3) / null=休符。1要素 = 8分音符
  const n = (s) => (s === "-" ? null : +s);
  const SONGS = {
    stage: {
      bpm: 140,
      lead: "5 - 8 7 5 - 3 5 | 0 - 3 5 7 - 8 - | 5 - 8 7 5 - 3 2 | 0 - - - - - - - | 12 - 10 8 7 - 8 10 | 12 - 15 - 13 12 10 - | 8 - 10 12 13 - 12 10 | 8 - 7 - 5 - - -".replace(/\|/g, "").trim().split(/\s+/).map(n),
      bass: "-7 -7 5 -7 -7 -7 5 -7 | -12 -12 0 -12 -9 -9 3 -9 | -7 -7 5 -7 -7 -7 5 -7 | -12 -12 0 -12 -12 0 -12 0 | -4 -4 8 -4 -5 -5 7 -5 | -7 -7 5 -7 -2 -2 10 -2 | -4 -4 8 -4 -5 -5 7 -5 | -7 -7 5 -7 -7 5 -7 5".replace(/\|/g, "").trim().split(/\s+/).map(n),
    },
    boss: {
      bpm: 168,
      lead: "0 1 0 - 7 - 6 - | 0 1 0 - 8 - 7 - | 0 1 0 - 7 - 6 - | 3 - 1 - 0 - - - | 12 11 12 - 15 - 13 - | 12 11 12 - 10 - 8 - | 7 8 7 - 6 - 3 - | 1 - 0 - -1 - 0 -".replace(/\|/g, "").trim().split(/\s+/).map(n),
      bass: "-12 0 -12 0 -12 0 -12 0 | -11 1 -11 1 -11 1 -11 1 | -12 0 -12 0 -12 0 -12 0 | -9 3 -11 1 -12 0 -12 0".replace(/\|/g, "").trim().split(/\s+/).map(n),
    },
  };
  const freq = (semi) => 220 * Math.pow(2, semi / 12);

  function schedule() {
    if (!bgm || !ac) return;
    const spb = 60 / bgm.bpm / 2;
    while (nextTime < ac.currentTime + 0.15) {
      const L = bgm.lead[step % bgm.lead.length], B = bgm.bass[step % bgm.bass.length];
      if (L !== null) tone(freq(L + 12), nextTime, spb * 0.9, "square", 0.22);
      if (B !== null) tone(freq(B), nextTime, spb * 0.8, "triangle", 0.45);
      if (step % 2 === 0) noise(nextTime, 0.03, step % 8 === 4 ? 0.15 : 0.06);
      nextTime += spb; step++;
    }
  }

  window.Sound = {
    unlock() { ensure(); },
    play(name) { if (!ensure() || muted) return; SFX[name] && SFX[name](ac.currentTime + 0.005); },
    music(name) {
      if (!ensure()) return;
      if (bgm === SONGS[name]) return;
      bgm = SONGS[name] || null; step = 0; nextTime = ac.currentTime + 0.05;
      if (!timer) timer = setInterval(schedule, 40);
    },
    stop() { bgm = null; },
    toggleMute() {
      muted = !muted;
      localStorage.setItem("mk_mute", muted ? "1" : "0");
      if (ensure()) master.gain.value = muted ? 0 : 0.18;
      return muted;
    },
    get muted() { return muted; },
  };
})();
