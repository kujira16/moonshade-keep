// MOONSHADE KEEP（月影の城） - ステージ1 試作
(function () {
  "use strict";
  const W = 160, H = 144, HUD = 16, T = 8;
  const canvas = document.getElementById("screen");
  const ctx = canvas.getContext("2d");
  ctx.imageSmoothingEnabled = false;
  const pal = () => Sprites.pal; // [明, 中明, 中暗, 暗]

  // ================= 入力 =================
  const held = { left: 0, right: 0, up: 0, down: 0, jump: 0, attack: 0, start: 0, select: 0 };
  let prev = { ...held }, pressed = {};
  const KEYMAP = {
    ArrowLeft: "left", KeyA: "left", ArrowRight: "right", KeyD: "right",
    ArrowUp: "up", KeyW: "up", ArrowDown: "down", KeyS: "down",
    KeyZ: "jump", Space: "jump", KeyK: "jump",
    KeyX: "attack", KeyJ: "attack",
    Enter: "start", Escape: "start", KeyP: "select",
  };
  const keyHeld = {}, latch = {}; // latch: フレーム間の素早いタップも取りこぼさない
  addEventListener("keydown", (e) => {
    if (e.code === "KeyM") { Sound.toggleMute(); return; }
    const k = KEYMAP[e.code];
    if (k) { if (!e.repeat) latch[k] = 1; keyHeld[k] = 1; e.preventDefault(); }
    Sound.unlock();
  });
  addEventListener("keyup", (e) => { const k = KEYMAP[e.code]; if (k) keyHeld[k] = 0; });

  // タッチボタン（data-btn 属性）。指を滑らせても反応するよう pointermove で判定
  const touchHeld = {};
  const pointers = new Map();
  function btnAt(x, y) {
    const el = document.elementFromPoint(x, y);
    const b = el && el.closest("[data-btn]");
    if (!b) return null;
    if (b.dataset.btn === "dpad") {
      const r = b.getBoundingClientRect();
      const dx = x - (r.left + r.width / 2), dy = y - (r.top + r.height / 2);
      if (Math.abs(dx) > Math.abs(dy)) return dx < 0 ? "left" : "right";
      return dy < 0 ? "up" : "down";
    }
    return b.dataset.btn;
  }
  function refreshTouch() {
    for (const k in touchHeld) touchHeld[k] = 0;
    for (const b of pointers.values()) if (b) touchHeld[b] = 1;
    document.querySelectorAll("[data-btn]").forEach((el) => {
      const on = el.dataset.btn === "dpad"
        ? ["left", "right", "up", "down"].some((d) => touchHeld[d])
        : touchHeld[el.dataset.btn];
      el.classList.toggle("on", !!on);
    });
  }
  const pad = document.getElementById("pad");
  if (pad) {
    pad.addEventListener("pointerdown", (e) => {
      e.preventDefault(); Sound.unlock();
      pad.setPointerCapture && pad.setPointerCapture(e.pointerId);
      const bt = btnAt(e.clientX, e.clientY); if (bt) latch[bt] = 1;
      pointers.set(e.pointerId, bt); refreshTouch();
      if (navigator.vibrate) navigator.vibrate(8);
    });
    pad.addEventListener("pointermove", (e) => {
      if (!pointers.has(e.pointerId)) return;
      pointers.set(e.pointerId, btnAt(e.clientX, e.clientY)); refreshTouch();
    });
    const up = (e) => { pointers.delete(e.pointerId); refreshTouch(); };
    pad.addEventListener("pointerup", up);
    pad.addEventListener("pointercancel", up);
    pad.addEventListener("contextmenu", (e) => e.preventDefault());
  }
  canvas.addEventListener("pointerdown", () => { Sound.unlock(); if (state === "title" || state === "over" || state === "clear") keyHeld.start = 1, setTimeout(() => keyHeld.start = 0, 80); });

  function pollInput() {
    const gp = navigator.getGamepads ? [...navigator.getGamepads()].find((g) => g) : null;
    for (const k in held) {
      held[k] = keyHeld[k] || touchHeld[k] || 0;
    }
    if (gp) {
      const ax = gp.axes[0] || 0, ay = gp.axes[1] || 0, b = (i) => gp.buttons[i] && gp.buttons[i].pressed;
      if (ax < -0.4 || b(14)) held.left = 1;
      if (ax > 0.4 || b(15)) held.right = 1;
      if (ay < -0.5 || b(12)) held.up = 1;
      if (ay > 0.5 || b(13)) held.down = 1;
      if (b(0)) held.jump = 1;
      if (b(1) || b(2)) held.attack = 1;
      if (b(9)) held.start = 1;
      if (b(8)) held.select = 1;
    }
    for (const k in held) { pressed[k] = (held[k] && !prev[k]) || latch[k]; if (latch[k]) held[k] = 1; latch[k] = 0; }
    prev = { ...held };
  }

  // ================= 文字（3x5 ドットフォント） =================
  const FONT = {};
  ("0:111101101101111 1:010110010010111 2:111001111100111 3:111001011001111 4:101101111001001 " +
   "5:111100111001111 6:111100111101111 7:111001001010010 8:111101111101111 9:111101111001111 " +
   "A:010101111101101 B:110101110101110 C:011100100100011 D:110101101101110 E:111100110100111 " +
   "F:111100110100100 G:011100101101011 H:101101111101101 I:111010010010111 J:001001001101010 " +
   "K:101101110101101 L:100100100100111 M:101111111101101 N:110101101101101 O:010101101101010 " +
   "P:110101110100100 Q:010101101110011 R:110101110101101 S:011100010001110 T:111010010010010 " +
   "U:101101101101111 V:101101101101010 W:101101111111101 X:101101010101101 Y:101101010010010 " +
   "Z:111001010100111 -:000000111000000 !:010010010000010 ::000010000010000 .:000000000000010 " +
   "/:001001010100100 ?:110001010000010 *:000101111010000 >:100010001010100 x:000101010101000")
    .split(" ").forEach((s) => { FONT[s[0]] = s.slice(2); });
  function text(str, x, y, shade = 0, scale = 1) {
    ctx.fillStyle = pal()[shade];
    str = String(str).toUpperCase();
    for (let i = 0; i < str.length; i++) {
      const g = FONT[str[i]];
      if (g) for (let p = 0; p < 15; p++) if (g[p] === "1")
        ctx.fillRect(x + i * 4 * scale + (p % 3) * scale, y + Math.floor(p / 3) * scale, scale, scale);
    }
  }
  const textC = (str, y, shade = 0, scale = 1) => text(str, Math.round((W - String(str).length * 4 * scale + scale) / 2), y, shade, scale);
  const pad0 = (n, l) => String(Math.max(0, Math.floor(n))).padStart(l, "0");

  // ================= ステージ =================
  const LV = window.LEVEL1;
  const MW = LV.map[0].length, MH = LV.map.length;
  let fg, bg, windows, spawns, gateClosed;
  function parseLevel() {
    fg = []; bg = []; windows = []; spawns = [];
    const colBg = [];
    for (let x = 0; x < MW; x++) {
      let c = null;
      for (let y = 0; y < MH; y++) { const ch = LV.map[y][x]; if (ch === "I") c = "I"; else if ((ch === "b" || ch === "W") && !c) c = "b"; }
      colBg.push(c);
    }
    for (let y = 0; y < MH; y++) {
      fg.push([]); bg.push([]);
      for (let x = 0; x < MW; x++) {
        const ch = LV.map[y][x];
        let f = null, b = null;
        if (ch === "#" || ch === "=" || ch === "^") f = ch;
        else if (ch === "b" || ch === "I") b = ch;
        else if (ch === "W") { b = "b"; windows.push([x, y]); }
        else if (ch !== ".") spawns.push({ ch, x, y });
        if (!b && ch !== "b" && colBg[x] && y >= 2 && y <= 13 && ch !== "#") b = colBg[x];
        fg[y].push(f); bg[y].push(b);
      }
    }
    gateClosed = false;
  }
  const tileAt = (tx, ty) => (ty < 0 || ty >= MH || tx < 0 || tx >= MW ? null : fg[ty][tx]);
  function solid(tx, ty) {
    if (tx < 0 || tx >= MW) return true;
    if (ty < 0 || ty >= MH) return false;
    if (gateClosed && (tx === LV.arenaX - 1 || tx === LV.arenaX) && ty >= 2 && ty <= 13) return true;
    return fg[ty][tx] === "#";
  }

  // 地形との当たり判定（b = {x,y,w,h,vx,vy}）
  function moveBody(b, oneWay = true) {
    b.onGround = false; b.hitWall = false;
    b.x += b.vx;
    const r0 = Math.floor(b.y / T), r1 = Math.floor((b.y + b.h - 0.01) / T);
    if (b.vx > 0) {
      const c = Math.floor((b.x + b.w - 0.01) / T);
      for (let r = r0; r <= r1; r++) if (solid(c, r)) { b.x = c * T - b.w; b.hitWall = true; break; }
    } else if (b.vx < 0) {
      const c = Math.floor(b.x / T);
      for (let r = r0; r <= r1; r++) if (solid(c, r)) { b.x = (c + 1) * T; b.hitWall = true; break; }
    }
    const prevBottom = b.y + b.h;
    b.y += b.vy;
    const c0 = Math.floor(b.x / T), c1 = Math.floor((b.x + b.w - 0.01) / T);
    if (b.vy > 0) {
      const r = Math.floor((b.y + b.h - 0.01) / T);
      for (let c = c0; c <= c1; c++) {
        if (solid(c, r) || (oneWay && tileAt(c, r) === "=" && prevBottom <= r * T + 0.5)) {
          b.y = r * T - b.h; b.vy = 0; b.onGround = true; break;
        }
      }
    } else if (b.vy < 0) {
      const r = Math.floor(b.y / T);
      for (let c = c0; c <= c1; c++) if (solid(c, r)) { b.y = (r + 1) * T; b.vy = 0; break; }
    }
  }
  const overlap = (a, b) => a.x < b.x + b.w && a.x + a.w > b.x && a.y < b.y + b.h && a.y + a.h > b.y;

  // ================= ゲーム状態 =================
  let state = "title", stateT = 0, frame = 0;
  let player, ents, parts, cam, score, lives, time, checkpoint, bossLock, boss, attackId, hiscore = +localStorage.getItem("mk_hi") || 0;
  let shake = 0, flash = 0, clearBonus = 0, msg = null;

  function newGame() {
    score = 0; lives = 2; checkpoint = null;
    startLife();
    state = "play"; stateT = 0;
  }
  function startLife() {
    parseLevel();
    ents = []; parts = []; bossLock = false; boss = null; attackId = 0; time = 300 * 60;
    let start = null;
    spawns.forEach((s, i) => {
      const x = s.x * T, y = s.y * T;
      if (s.ch === "P") start = { x: x + 4, y: y + 2 };
      else if (s.ch === "C") ents.push({ type: "candle", x: x, y: y, w: 8, h: 16, hp: 1, drop: i % 3 === 2 ? "gem" : "heart" });
      else if (s.ch === "B") ents.push({ type: "bat", x: x + 2, y: y, w: 12, h: 7, hp: 1, mode: "hang", t: 0 });
      else if (s.ch === "S") ents.push({ type: "skel", x: x + 4, y: y + 1, w: 8, h: 15, hp: 2, face: -1, vx: 0, vy: 0, t: 60 + (i * 37) % 60, pause: 0 });
      else if (s.ch === "G") ents.push({ type: "ghost", x: x + 2, y: y + 2, w: 12, h: 12, hp: 2, t: 0, awake: false });
      else if (s.ch === "R") ents.push({ type: "check", x: x, y: 0, w: 8, h: 128, sx: x, sy: y + 2 });
      else if (s.ch === "K") boss = { x: x + 4, y: -30, hp: 16, max: 16, state: "wait", t: 0, inv: 0, homeY: 36 };
    });
    const p = checkpoint || start;
    player = { x: p.x, y: p.y, w: 8, h: 14, vx: 0, vy: 0, face: 1, hp: 8, max: 8, onGround: false,
      coyote: 0, jumpBuf: 0, atk: 0, atkAir: false, hurt: 0, inv: 60, anim: 0, dead: false };
    cam = clamp(player.x - 76, 0, MW * T - W);
    Sound.music("stage");
  }
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  function addScore(n) { score += n; }
  function spark(x, y, n = 1, spread = 0) {
    for (let i = 0; i < n; i++) parts.push({ kind: "spark", x: x + (Math.random() - 0.5) * spread, y: y + (Math.random() - 0.5) * spread, t: -i * 3 });
  }
  function hurtPlayer(dmg, fromX, bounce = 1.8) {
    if (player.inv > 0 || player.dead) return;
    player.hp -= dmg;
    player.inv = 70; player.hurt = 16;
    player.face = fromX > player.x + 4 ? 1 : -1;
    player.vx = -player.face * 1.0; player.vy = -bounce; player.atk = 0;
    shake = 6; Sound.play("hurt");
    if (player.hp <= 0) killPlayer();
  }
  function killPlayer() {
    if (player.dead) return;
    player.dead = true; player.hp = 0; stateT = 0; state = "dying";
    Sound.stop(); Sound.play("die");
  }

  // ムチの当たり判定
  function whipBox() {
    const p = player;
    if (p.atk < 6 || p.atk > 13) return null;
    const hx = p.x + 4 + p.face * 6;
    return { x: p.face > 0 ? hx : hx - 24, y: p.y + 3, w: 24, h: 7 };
  }

  // ================= 更新 =================
  function updatePlayer() {
    const p = player;
    if (p.dead) { p.vy = Math.min(p.vy + 0.15, 3); p.y += p.vy * 0.3; return; }
    if (p.inv > 0) p.inv--;
    const ctl = p.hurt <= 0;
    if (p.hurt > 0) p.hurt--;

    // 攻撃
    if (ctl && pressed.attack && p.atk === 0) {
      p.atk = 1; p.atkAir = !p.onGround; attackId++; Sound.play("whip");
    }
    if (p.atk > 0) { p.atk++; if (p.atk > 22) p.atk = 0; }

    // 横移動（地上攻撃中は停止）
    // 加速・減速つきの横移動（なめらかに動き出して止まる）
    const MAXV = 0.85, ACC = p.onGround ? 0.07 : 0.05, DEC = p.onGround ? 0.09 : 0.03;
    if (ctl) {
      const dir = (held.right ? 1 : 0) - (held.left ? 1 : 0);
      const target = p.atk && !p.atkAir ? 0 : dir * MAXV;
      if (dir && !p.atk) p.face = dir;
      const rate = target === 0 || Math.sign(target) !== Math.sign(p.vx) ? DEC + (target ? ACC : 0) : ACC;
      p.vx += clamp(target - p.vx, -rate, rate);
    }
    // ジャンプ（コヨーテタイム + 先行入力 + 可変ジャンプ）
    p.coyote = p.onGround ? 6 : Math.max(0, p.coyote - 1);
    p.jumpBuf = pressed.jump ? 7 : Math.max(0, p.jumpBuf - 1);
    if (ctl && p.jumpBuf && p.coyote && !(p.atk && !p.atkAir)) {
      p.vy = -3.15; p.coyote = 0; p.jumpBuf = 0; Sound.play("jump");
    }
    if (!held.jump && p.vy < -1.0 && ctl) p.vy += (-1.0 - p.vy) * 0.35; // 離すとふわっと減速
    p.vy = Math.min(p.vy + 0.13, 3);
    const wasGround = p.onGround;
    moveBody(p);
    if (p.onGround && !wasGround && p.atkAir) p.atkAir = false;

    // 画面端
    const minX = bossLock ? cam : 0, maxX = bossLock ? cam + W - p.w : MW * T - p.w;
    p.x = clamp(p.x, minX, maxX);
    if (p.y > MH * T + 8) killPlayer();

    // トゲ
    const c0 = Math.floor((p.x + 1) / T), c1 = Math.floor((p.x + p.w - 2) / T), r = Math.floor((p.y + p.h - 1) / T);
    for (let c = c0; c <= c1; c++) if (tileAt(c, r) === "^" && p.y + p.h - 1 > r * T + 3) hurtPlayer(2, p.x + 4 - p.face * 8, 3); // トゲは高く跳ね上げて抜け出しやすく

    p.anim = Math.abs(p.vx) > 0.1 && p.onGround ? p.anim + Math.abs(p.vx) / 0.85 : 0;
  }

  function updateEnts() {
    const wb = whipBox(), p = player;
    const pbox = { x: p.x + 1, y: p.y + 1, w: p.w - 2, h: p.h - 1 };
    for (const e of ents) {
      if (e.dead) continue;
      const near = e.x > cam - 32 && e.x < cam + W + 32;
      if (!near && e.type !== "fire" && e.type !== "bone" && e.type !== "item") continue;
      e.t = (e.t || 0) + 1;
      const pdx = p.x + 4 - (e.x + e.w / 2);
      switch (e.type) {
        case "check":
          if (p.x > e.x && !p.dead) { checkpoint = { x: e.sx, y: e.sy }; e.dead = true; msg = { s: "CHECKPOINT", t: 90 }; Sound.play("select"); }
          continue;
        case "bat":
          if (e.mode === "hang") { if (Math.abs(pdx) < 60) { e.mode = "fly"; e.dir = Math.sign(pdx) || -1; e.baseY = e.y; e.t = 0; } }
          else {
            e.baseY += clamp(p.y - e.baseY, -1, 1) * 0.35;
            e.x += e.dir * 0.9;
            e.y = e.baseY + Math.sin(e.t * 0.12) * 10;
            if (e.x < cam - 40 || e.x > cam + W + 40) e.dead = true;
          }
          break;
        case "skel": {
          if (e.pause > 0) { e.pause--; e.vx = 0; if (e.pause === 10) throwBone(e); }
          else {
            e.vx = e.face * 0.35;
            e.t--;
            if (e.t <= 0) {
              e.t = 100 + Math.floor(Math.random() * 60);
              if (Math.abs(pdx) < 100) { e.face = Math.sign(pdx) || e.face; e.pause = 24; }
            }
          }
          e.vy = Math.min((e.vy || 0) + 0.2, 4);
          moveBody(e, true);
          const aheadX = Math.floor((e.x + (e.face > 0 ? e.w + 1 : -1)) / T), footY = Math.floor((e.y + e.h + 1) / T);
          if (e.onGround && (e.hitWall || (!solid(aheadX, footY) && tileAt(aheadX, footY) !== "=") || tileAt(aheadX, footY - 1) === "^")) e.face *= -1;
          if (e.y > MH * T) e.dead = true;
          break;
        }
        case "ghost":
          if (!e.awake && e.x < cam + W - 8) e.awake = true;
          if (e.awake) {
            const dy = p.y - e.y;
            const d = Math.hypot(pdx, dy) || 1;
            e.x += (pdx / d) * 0.32; e.y += (dy / d) * 0.32 + Math.sin(e.t * 0.08) * 0.3;
          }
          break;
        case "bone":
          e.x += e.vx; e.vy += 0.1; e.y += e.vy;
          if (e.y > MH * T + 16) e.dead = true;
          break;
        case "fire":
          e.x += e.vx; e.y += e.vy;
          if (e.x < cam - 16 || e.x > cam + W + 16 || e.y > MH * T || e.y < -16 || solid(Math.floor((e.x + 4) / T), Math.floor((e.y + 4) / T))) e.dead = true;
          break;
        case "item":
          e.vy = Math.min(e.vy + 0.15, 2); moveBody(e, true);
          if (e.t > 420) e.dead = true;
          if (overlap(e, pbox)) {
            e.dead = true; Sound.play("pickup");
            if (e.kind === "heart") player.hp = Math.min(player.max, player.hp + 2), addScore(10);
            else if (e.kind === "gem") addScore(500);
            else if (e.kind === "orb") { stageClear(); }
          }
          continue;
      }
      // ムチが当たったか
      if (wb && e.hitBy !== attackId && overlap(wb, e)) {
        e.hitBy = attackId;
        e.hp = (e.hp || 1) - 1;
        if (e.type === "skel" || e.type === "ghost") e.x += p.face * 4;
        if (e.hp <= 0) {
          e.dead = true;
          spark(e.x + e.w / 2 - 4, e.y + e.h / 2 - 4, e.type === "candle" ? 1 : 2, 6);
          if (e.type === "candle") { Sound.play("candle"); addScore(50); ents.push({ type: "item", kind: e.drop, x: e.x, y: e.y + 4, w: 8, h: 7, vx: 0, vy: -1.5, t: 0 }); }
          else { Sound.play("hit"); addScore({ bat: 100, skel: 200, ghost: 300, bone: 10, fire: 10 }[e.type] || 0); }
        } else Sound.play("hit");
        continue;
      }
      // プレイヤーに当たったか
      if (e.type !== "candle" && overlap(e, pbox)) {
        hurtPlayer(1, e.x + e.w / 2);
        if (e.type === "bone" || e.type === "fire") e.dead = true;
      }
    }
    ents = ents.filter((e) => !e.dead);
  }
  function throwBone(e) {
    ents.push({ type: "bone", x: e.x, y: e.y, w: 6, h: 6, vx: e.face * 1.1, vy: -2.7, hp: 1, t: 0 });
  }

  function updateBoss() {
    const b = boss, p = player;
    if (!b || b.state === "dead") return;
    const arenaL = LV.arenaX * T, cx = arenaL + W / 2;
    if (!bossLock && b.state === "wait" && p.x > arenaL + 20 && !p.dead) {
      bossLock = true; gateClosed = true; shake = 10; Sound.play("boss"); Sound.music("boss");
      b.state = "intro"; b.t = 0; b.x = cx;
    }
    if (b.state === "wait") return;
    b.t++;
    if (b.inv > 0) b.inv--;
    const angry = b.hp <= b.max / 2;
    const box = { x: b.x - 11, y: b.y - 8, w: 22, h: 15 };
    switch (b.state) {
      case "intro":
        b.y += (b.homeY - b.y) * 0.04;
        if (b.t > 90) { b.state = "hover"; b.t = 0; }
        break;
      case "hover": {
        const tx = cx + Math.sin(frame * 0.02) * 52;
        b.x += (tx - b.x) * 0.05;
        b.y += (b.homeY + Math.sin(frame * 0.07) * 6 - b.y) * 0.1;
        if (b.t > (angry ? 80 : 130)) { b.t = 0; b.state = Math.random() < 0.5 ? "shoot" : "swoop"; if (b.state === "swoop") { b.tx = p.x + 4; b.ty = p.y + 2; } }
        break;
      }
      case "shoot":
        b.y += Math.sin(b.t * 0.3) * 0.3;
        if ([20, 40, 60].includes(b.t) || (angry && b.t === 80)) {
          const dx = p.x + 4 - b.x, dy = p.y + 7 - b.y, d = Math.hypot(dx, dy) || 1, sp = angry ? 1.6 : 1.25;
          ents.push({ type: "fire", x: b.x - 4, y: b.y, w: 6, h: 6, vx: (dx / d) * sp, vy: (dy / d) * sp, hp: 1, t: 0 });
          Sound.play("whip");
        }
        if (b.t > (angry ? 100 : 80)) { b.state = "hover"; b.t = 0; }
        break;
      case "swoop": {
        if (b.t < 24) { b.y -= 0.4; b.x += Math.sin(b.t) * 0.6; break; } // 予備動作でブルブル
        const dx = b.tx - b.x, dy = b.ty - b.y, d = Math.hypot(dx, dy);
        const sp = angry ? 2.8 : 2.3;
        if (d < sp || b.t > 110) { b.state = "rise"; b.t = 0; break; }
        b.x += (dx / d) * sp; b.y += (dy / d) * sp;
        break;
      }
      case "rise":
        b.y += (b.homeY - b.y) * 0.05;
        if (b.t > 50) { b.state = "hover"; b.t = 0; }
        break;
      case "dying":
        if (b.t % 6 === 0) { spark(b.x - 4, b.y - 4, 1, 32); Sound.play("hit"); }
        shake = 2;
        if (b.t > 110) {
          b.state = "dead"; Sound.play("explode"); flash = 12;
          spark(b.x - 4, b.y - 4, 10, 30);
          ents.push({ type: "item", kind: "orb", x: b.x - 4, y: b.y, w: 8, h: 8, vx: 0, vy: -2, t: -9999 });
          addScore(5000);
          Sound.music("stage");
        }
        return;
    }
    b.y = Math.min(b.y, 13 * T - 10);
    // ムチ
    const wb = whipBox();
    if (wb && b.inv === 0 && b.hitBy !== attackId && overlap(wb, box)) {
      b.hitBy = attackId; b.hp--; b.inv = 14; Sound.play("boss"); shake = 3;
      spark(wb.x + (p.face > 0 ? wb.w - 6 : 0), wb.y - 1);
      if (b.hp <= 0) { b.state = "dying"; b.t = 0; Sound.stop(); ents = ents.filter((e) => e.type !== "fire"); }
    }
    const pbox = { x: p.x + 1, y: p.y + 1, w: p.w - 2, h: p.h - 1 };
    if (b.state !== "dying" && overlap(box, pbox)) hurtPlayer(2, b.x);
  }

  function stageClear() {
    state = "clear"; stateT = 0; clearBonus = Math.floor(time / 60) * 10; Sound.stop(); Sound.play("clear");
  }

  function update() {
    frame++; stateT++;
    pollInput();
    if (pressed.select) Sprites.cyclePalette();
    if (msg && --msg.t <= 0) msg = null;
    if (shake > 0) shake--;
    if (flash > 0) flash--;

    if (state === "title") {
      if (pressed.start || pressed.jump || pressed.attack) { Sound.unlock(); Sound.play("select"); newGame(); }
      return;
    }
    if (state === "over") {
      if (stateT > 60 && (pressed.start || pressed.jump)) { state = "title"; stateT = 0; }
      return;
    }
    if (state === "clear") {
      if (clearBonus > 0 && stateT > 60) { const d = Math.min(clearBonus, 50); clearBonus -= d; score += d; if (frame % 4 === 0) Sound.play("select"); }
      if (score > hiscore) { hiscore = score; localStorage.setItem("mk_hi", hiscore); }
      if (stateT > 120 && clearBonus === 0 && (pressed.start || pressed.jump)) { state = "title"; stateT = 0; }
      return;
    }
    if (state === "pause") {
      if (pressed.start) { state = "play"; Sound.music(bossLock ? "boss" : "stage"); }
      return;
    }
    if (state === "play" && pressed.start) { state = "pause"; Sound.stop(); return; }

    if (state === "play") {
      time--;
      if (time <= 0) killPlayer();
    }
    updatePlayer();
    updateEnts();
    updateBoss();
    for (const q of parts) q.t++;
    parts = parts.filter((q) => q.t < 15);

    if (!bossLock) cam += (clamp(player.x - 76, 0, MW * T - W) - cam) * 0.12;
    else cam += (LV.arenaX * T - cam) * 0.1;

    if (state === "dying" && stateT > 100) {
      lives--;
      if (score > hiscore) { hiscore = score; localStorage.setItem("mk_hi", hiscore); }
      if (lives < 0) { state = "over"; stateT = 0; Sound.stop(); }
      else { startLife(); state = "play"; stateT = 0; }
    }
  }

  // ================= 描画 =================
  function spr(name, f, x, y, flip = false) {
    const s = Sprites.get(name, f);
    ctx.drawImage(flip ? s.flip : s.img, Math.round(x), Math.round(y));
  }

  // 遠景の城シルエット（手続き生成）
  const SKY = [];
  (function () {
    let seed = 7;
    const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
    for (let x = 0; x < 320; x++) SKY.push(96);
    for (let k = 0; k < 14; k++) {
      const cx = Math.floor(rnd() * 320), w = 3 + Math.floor(rnd() * 6), h = 14 + Math.floor(rnd() * 34);
      for (let x = cx - w; x <= cx + w; x++) {
        const xx = (x + 320) % 320;
        const spire = Math.max(0, 10 - Math.abs(x - cx) * 2.2);
        const battle = Math.abs(x - cx) === w && false;
        SKY[xx] = Math.min(SKY[xx], 112 - h - spire - (battle ? 2 : 0));
      }
    }
    for (let x = 0; x < 320; x++) if (x % 6 < 3) SKY[x] = Math.min(SKY[x] + 0, SKY[x]);
  })();
  const STARS = Array.from({ length: 28 }, (_, i) => [(i * 53) % 220, 4 + ((i * 29) % 70)]);

  function drawBackdrop(oy) {
    const P = pal();
    ctx.fillStyle = P[3]; ctx.fillRect(0, oy, W, 128);
    ctx.fillStyle = P[2];
    for (const [sx, sy] of STARS) { const x = Math.round(((sx - cam * 0.03) % 220 + 220) % 220); if (x < W && (frame + sx) % 140 > 4) ctx.fillRect(x, oy + sy, 1, 1); }
    // 月
    const mx = Math.round(118 - cam * 0.04), my = oy + 26;
    ctx.fillStyle = P[0];
    for (let y = -12; y <= 12; y++) { const w = Math.floor(Math.sqrt(144 - y * y)); ctx.fillRect(mx - w, my + y, w * 2, 1); }
    ctx.fillStyle = P[1];
    ctx.fillRect(mx - 5, my - 4, 4, 3); ctx.fillRect(mx + 3, my + 2, 3, 3); ctx.fillRect(mx - 2, my + 6, 2, 2);
    // 城のシルエット
    ctx.fillStyle = P[2];
    for (let x = 0; x < W; x++) {
      const h = SKY[Math.floor(((x + cam * 0.3) % 320 + 320) % 320)];
      ctx.fillRect(x, oy + h, 1, 128 - h);
    }
    // 窓明かり
    ctx.fillStyle = P[1];
    for (let x = 0; x < W; x++) { const wx = Math.floor(x + cam * 0.3); if (wx % 37 === 0) { const h = SKY[((wx % 320) + 320) % 320]; if (h < 80) ctx.fillRect(x, oy + h + 10, 1, 2); } }
    // 木々の手前シルエット
    ctx.fillStyle = P[3];
    for (let x = 0; x < W; x++) { const wx = x + cam * 0.6; const h = 110 + Math.sin(wx * 0.11) * 4 + Math.sin(wx * 0.37) * 2; ctx.fillRect(x, oy + Math.round(h), 1, 128); }
  }

  function drawWorld() {
    const oy = HUD;
    const sx = shake ? Math.round((Math.random() - 0.5) * 3) : 0;
    ctx.save();
    ctx.beginPath(); ctx.rect(0, HUD, W, H - HUD); ctx.clip();
    ctx.translate(sx, 0);
    drawBackdrop(oy);
    const cx = Math.floor(cam), c0 = Math.floor(cx / T), c1 = c0 + W / T + 1;
    ctx.translate(-cx, oy);
    for (let y = 0; y < MH; y++) for (let x = c0; x <= c1 && x < MW; x++) {
      const b = bg[y][x];
      if (b === "b") spr("t_back", 0, x * T, y * T);
      else if (b === "I") spr("t_pillar", 0, x * T, y * T);
    }
    for (const [x, y] of windows) if (x * T > cx - 16 && x * T < cx + W) spr("t_window", 0, x * T, y * T);
    for (let y = 0; y < MH; y++) for (let x = c0; x <= c1 && x < MW; x++) {
      const f = fg[y][x];
      if (f === "#") spr(y > 0 && fg[y - 1][x] !== "#" ? "t_brick_top" : "t_brick", 0, x * T, y * T);
      else if (f === "=") spr("t_ledge", 0, x * T, y * T);
      else if (f === "^") spr("t_spikes", 0, x * T, y * T);
    }
    if (gateClosed) for (let y = 2; y <= 13; y++) for (const x of [LV.arenaX - 1, LV.arenaX]) spr(y % 2 ? "t_pillar" : "t_brick", 0, x * T, y * T);

    // 敵・アイテム
    for (const e of ents) {
      const f = Math.floor(frame / 8);
      switch (e.type) {
        case "candle": spr("candle", f, e.x, e.y); break;
        case "bat": spr(e.mode === "hang" ? "bat_hang" : "bat", Math.floor(frame / 6), e.x - 2, e.y - 1); break;
        case "skel": spr("skeleton", e.vx ? Math.floor(e.x / 6) : 0, e.x - 4, e.y - 1, e.face < 0); break;
        case "ghost": if (frame % 3 || !e.awake) spr("ghost", f, e.x - 2, e.y - 2, player.x < e.x); break;
        case "bone": spr("bone", Math.floor(frame / 5), e.x - 1, e.y - 1); break;
        case "fire": spr("fireball", Math.floor(frame / 4), e.x - 1, e.y - 1); break;
        case "item":
          if (e.t > 360 && frame % 6 < 3) break;
          spr(e.kind === "orb" ? "orb" : e.kind, Math.floor(frame / 10), e.x, e.y - 1);
          break;
      }
    }
    // ボス
    const b = boss;
    if (b && b.state !== "wait" && b.state !== "dead" && !(b.inv && frame % 4 < 2) && !(b.state === "dying" && frame % 4 < 2)) {
      const wf = Math.floor(frame / (b.state === "swoop" ? 4 : 9)) % 2;
      spr("boss_wing", wf, b.x + 5, b.y - 13);
      spr("boss_wing", wf, b.x - 21, b.y - 13, true);
      spr("boss_skull", 0, b.x - 8, b.y - 8);
      if (b.state === "swoop" && b.t < 24 && frame % 4 < 2) { ctx.fillStyle = pal()[0]; ctx.fillRect(b.x - 6, b.y - 3, 3, 2); ctx.fillRect(b.x + 3, b.y - 3, 3, 2); }
    }
    drawPlayer();
    for (const q of parts) if (q.t >= 0) spr("spark", Math.floor(q.t / 5), q.x, q.y);
    ctx.restore();
  }

  function drawPlayer() {
    const p = player;
    if (p.inv > 0 && !p.dead && frame % 4 < 2) return;
    if (p.dead && stateT > 40 && frame % 4 < 2) return;
    const flip = p.face < 0, sx = p.x - 4, sy = p.y - 2;
    let name = "player_idle", f = 0;
    if (p.atk) name = p.onGround ? "player_attack" : "player_attack_air";
    else if (!p.onGround) name = "player_jump";
    else if (Math.abs(p.vx) > 0.1) { name = "player_walk"; f = Math.floor(p.anim / 8); }
    spr(name, f, sx, sy, flip);
    // ムチ（鎖を点で描く）
    if (p.atk) {
      const P = pal(), hx = p.x + 4 + p.face * 7, hy = p.y + 6;
      ctx.fillStyle = P[0];
      if (p.atk < 6) {
        for (let i = 0; i < 4; i++) ctx.fillRect(hx - p.face * (4 + i * 2), hy - 3 - i * 2, 2, 2);
      } else {
        const len = p.atk < 15 ? 24 : 12, yy = p.atk < 15 ? hy - 1 : hy + 2;
        for (let i = 0; i < len; i += 3) ctx.fillRect(p.face > 0 ? hx + i : hx - i - 2, yy, 2, 2);
        if (p.atk < 15) { const tx = p.face > 0 ? hx + len : hx - len - 3; ctx.fillRect(tx, yy - 1, 3, 4); ctx.fillStyle = P[1]; ctx.fillRect(tx + 1, yy, 1, 2); }
      }
    }
  }

  function drawHUD() {
    const P = pal();
    ctx.fillStyle = P[3]; ctx.fillRect(0, 0, W, HUD);
    ctx.fillStyle = P[2]; ctx.fillRect(0, HUD - 1, W, 1);
    text("SCORE" + pad0(score, 6), 2, 2, 0);
    text("TIME" + pad0(time / 60, 3), 72, 2, 0);
    text("*" + Math.max(0, lives), 136, 2, 1);
    text("P", 2, 9, 0);
    for (let i = 0; i < player.max; i++) { ctx.fillStyle = i < player.hp ? P[0] : P[2]; ctx.fillRect(8 + i * 4, 9, 3, 5); }
    if (bossLock && boss) {
      text("E", 84, 9, 0);
      for (let i = 0; i < boss.max; i++) { ctx.fillStyle = i < boss.hp ? P[1] : P[2]; ctx.fillRect(90 + i * 4, 9, 3, 5); }
    }
  }

  function drawTitle() {
    cam = frame * 0.5;
    drawBackdrop(HUD - 8);
    const P = pal();
    ctx.fillStyle = P[3]; ctx.fillRect(0, 0, W, 10); ctx.fillRect(0, 134, W, 10);
    textC("MOONSHADE", 29, 3, 3); textC("KEEP", 49, 3, 3);
    textC("MOONSHADE", 28, 0, 3);
    textC("KEEP", 48, 1, 3);
    textC("- STAGE 1 PROTOTYPE -", 70, 1);
    if (Math.floor(stateT / 30) % 2 === 0) textC(isTouch ? "TAP START" : "PRESS ENTER", 92, 0);
    textC(isTouch ? "A:JUMP  B:WHIP" : "Z:JUMP  X:WHIP  M:SOUND", 110, 1);
    textC("HI " + pad0(hiscore, 6), 136, 1);
    textC(isTouch ? "SELECT:COLOR" : "P:COLOR", 120, 2);
  }

  function render() {
    const P = pal();
    if (state === "title") { drawTitle(); return; }
    if (state === "over") {
      ctx.fillStyle = P[3]; ctx.fillRect(0, 0, W, H);
      textC("GAME OVER", 56, 0, 2);
      textC("SCORE " + pad0(score, 6), 80, 1);
      if (stateT > 60 && Math.floor(stateT / 30) % 2 === 0) textC("PRESS START", 100, 0);
      return;
    }
    drawWorld();
    drawHUD();
    if (msg) textC(msg.s, 30, 0);
    if (state === "pause") { ctx.fillStyle = P[3]; ctx.fillRect(50, 62, 60, 20); textC("PAUSE", 70, 0); }
    if (state === "clear") {
      ctx.fillStyle = P[3]; ctx.fillRect(12, 40, 136, 72);
      ctx.fillStyle = P[1]; ctx.fillRect(12, 40, 136, 1); ctx.fillRect(12, 111, 136, 1);
      textC("STAGE CLEAR!", 48, 0, 2);
      textC("TIME BONUS " + pad0(clearBonus, 4), 70, 1);
      textC("SCORE " + pad0(score, 6), 80, 0);
      if (stateT > 120 && !clearBonus) textC("THANKS FOR PLAYING", 96, 1);
    }
    if (flash) { ctx.fillStyle = P[0]; ctx.globalAlpha = flash / 12; ctx.fillRect(0, HUD, W, H - HUD); ctx.globalAlpha = 1; }
  }

  // ================= 画面サイズ =================
  const isTouch = matchMedia("(pointer: coarse)").matches || "ontouchstart" in window;
  document.body.classList.toggle("touch", isTouch);
  function fit() {
    const area = document.getElementById("view");
    const r = area.getBoundingClientRect();
    let s = Math.min(r.width / W, r.height / H);
    if (s >= 2) s = Math.floor(s);
    canvas.style.width = Math.floor(W * s) + "px";
    canvas.style.height = Math.floor(H * s) + "px";
  }
  addEventListener("resize", fit);
  addEventListener("orientationchange", () => setTimeout(fit, 200));

  // ================= ループ =================
  let last = 0, acc = 0;
  function loop(ts) {
    const dt = Math.min(0.1, (ts - last) / 1000 || 0);
    last = ts; acc += dt;
    let n = 0;
    while (acc >= 1 / 60 && n < 5) { update(); acc -= 1 / 60; n++; }
    render();
    requestAnimationFrame(loop);
  }
  // デバッグ用フック（?debug=1）
  window.MK = { get state() { return state; }, get player() { return player; }, get boss() { return boss; }, get cam() { return cam; }, newGame, keyHeld, warp(tx) { player.x = tx * T; player.y = 40; cam = clamp(player.x - 76, 0, MW * T - W); } };

  (async function boot() {
    await Sprites.loadOverrides();
    Sprites.bakeAll();
    parseLevel();
    fit(); setTimeout(fit, 100);
    requestAnimationFrame(loop);
  })();
})();
