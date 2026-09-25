// Generates the interface/canvas/*.dc.html design-canvas screens (one per board state) from
// shared design tokens. Run: node interface/canvas/build.mjs
import { writeFileSync } from "node:fs";

const C = {
  paper:  "oklch(0.987 0.003 85)",
  panel:  "oklch(0.971 0.004 85)",
  ink:    "oklch(0.27 0.012 70)",
  muted:  "oklch(0.46 0.01 70)",
  faint:  "oklch(0.58 0.008 70)",
  line:   "oklch(0.905 0.005 80)",
  line2:  "oklch(0.82 0.008 80)",
  pos:    "oklch(0.52 0.075 155)",
  neg:    "oklch(0.53 0.085 40)",
  stop:   "oklch(0.44 0.05 38)",
  wait:   "oklch(0.62 0.025 80)",
  ask:    "oklch(0.52 0.045 250)",
  hover:  "oklch(0.945 0.005 80)",
};
const SERIF = `Newsreader, Georgia, serif`;
const SANS = `Karla, 'Helvetica Neue', Arial, sans-serif`;
const W = 1200, H = 760, SIDE = 420;

const shell = (body, h = H) => `<!doctype html>
<html>
<head>
<meta charset="utf-8">
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Newsreader:ital,opsz,wght@0,6..72,300;0,6..72,400;0,6..72,500;1,6..72,300&family=Karla:wght@400;500;600&display=swap">
<style>
  body { margin: 0; font-family: ${SANS}; -webkit-font-smoothing: antialiased; }
  * { box-sizing: border-box; }
  a { color: ${C.neg}; } a:hover { color: oklch(0.44 0.085 40); }
  .btn { transition: background-color 180ms ease, border-color 180ms ease; cursor: pointer; }
  .btn:focus-visible { outline: 2px solid ${C.neg}; outline-offset: 3px; }
  .btn-ghost:hover { background: ${C.hover}; }
  .btn-solid:hover { background: oklch(0.36 0.012 70); }
  .tap { cursor: pointer; transition: background-color 160ms ease; }
  .tap:hover { background: ${C.hover}; }
  @keyframes breathe { 0%, 100% { opacity: 0.35; } 50% { opacity: 1; } }
  .pulse { animation: breathe 2.4s ease-in-out infinite; }
  @media (prefers-reduced-motion: reduce) { .pulse { animation: none; opacity: 0.7; } }
</style>
</helmet>
<div style="width: ${W}px; height: ${h}px; background: ${C.paper}; color: ${C.ink}; display: flex; flex-direction: column; position: relative;">
${body}
</div>
</x-dc>
</body>
</html>
`;

const header = (product = "Photo app", { chevron = true, open = false } = {}) => `
  <div style="flex-shrink: 0; height: 56px; border-bottom: 1px solid ${C.line}; display: flex; align-items: center; justify-content: space-between; padding: 0 20px;">
    <div class="tap" style="display: flex; align-items: center; gap: 10px; padding: 7px 10px; border-radius: 4px; ${open ? `background: ${C.hover};` : ""}">
      <svg width="15" height="15" viewBox="0 0 16 16" fill="none" aria-hidden="true"><rect x="1" y="1" width="6" height="6" rx="1.4" fill="${C.ink}"/><rect x="9" y="1" width="6" height="6" rx="1.4" fill="${C.line2}"/><rect x="1" y="9" width="6" height="6" rx="1.4" fill="${C.line2}"/><rect x="9" y="9" width="6" height="6" rx="1.4" fill="${C.ink}"/></svg>
      <span style="font-family: ${SANS}; font-size: 14px; font-weight: 600; letter-spacing: -0.005em;">${product}</span>
      ${chevron ? `<svg width="11" height="11" viewBox="0 0 11 11" fill="none" aria-hidden="true"><path d="M2.6 4.2 L5.5 7.1 L8.4 4.2" stroke="${C.faint}" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round"/></svg>` : ""}
    </div>
    <div class="tap" style="padding: 8px; border-radius: 4px; display: flex;" aria-label="Settings">
      <svg width="16" height="16" viewBox="0 0 17 17" fill="none" aria-hidden="true"><circle cx="8.5" cy="8.5" r="2.6" stroke="${C.faint}" stroke-width="1.35"/><path d="M8.5 1.6v1.8M8.5 13.6v1.8M15.4 8.5h-1.8M3.4 8.5H1.6M13.4 3.6l-1.3 1.3M4.9 12.1l-1.3 1.3M13.4 13.4l-1.3-1.3M4.9 4.9L3.6 3.6" stroke="${C.faint}" stroke-width="1.35" stroke-linecap="round"/></svg>
    </div>
  </div>`;

/* two-pane body: chat left, product sidebar right */
const panes = (chat, side) => `
  <div style="flex-grow: 1; display: flex; min-height: 0;">
    <div style="flex-grow: 1; display: flex; flex-direction: column; min-width: 0;">${chat}</div>
    <div style="width: ${SIDE}px; flex-shrink: 0; border-left: 1px solid ${C.line}; background: ${C.panel}; display: flex; flex-direction: column;">${side}</div>
  </div>`;

const sidebar = (rows, { count = "" } = {}) => `
      <div style="flex-shrink: 0; padding: 20px 22px 14px; display: flex; align-items: baseline; justify-content: space-between; gap: 12px;">
        <span style="font-family: ${SANS}; font-size: 13.5px; font-weight: 600;">Your product</span>
        ${count ? `<span style="font-family: ${SANS}; font-size: 12px; color: ${C.faint};">${count}</span>` : ""}
      </div>
      <div style="flex-grow: 1; overflow: hidden; display: flex; flex-direction: column;">${rows}</div>
      <div style="flex-shrink: 0; border-top: 1px solid ${C.line}; padding: 12px 18px;">
        <div class="tap" style="display: flex; align-items: center; gap: 9px; padding: 8px 10px; border-radius: 4px;">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 2.6v7.6M8 10.2 4.9 7.1M8 10.2l3.1-3.1M2.8 12.2v1.2h10.4v-1.2" stroke="${C.faint}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>
          <span style="font-family: ${SANS}; font-size: 13px; font-weight: 600; color: ${C.muted};">Export what you have</span>
        </div>
      </div>`;

const glyph = (state, cls = "", mt = 2) => {
  const w = (inner) => `<svg width="16" height="16" viewBox="0 0 18 18" fill="none" ${cls ? `class="${cls}"` : ""} style="flex-shrink: 0; margin-top: ${mt}px;" aria-hidden="true">${inner}</svg>`;
  if (state === "working") return w(`<circle cx="9" cy="9" r="5.8" fill="${C.pos}"/>`);
  if (state === "pending") return w(`<circle cx="9" cy="9" r="5.8" stroke="${C.wait}" stroke-width="1.5"/><path d="M9 3.2 A5.8 5.8 0 0 1 9 14.8 Z" fill="${C.wait}"/>`);
  if (state === "failed")  return w(`<circle cx="9" cy="9" r="5.8" stroke="${C.neg}" stroke-width="1.8"/>`);
  if (state === "stopped") return w(`<circle cx="9" cy="9" r="5.8" stroke="${C.stop}" stroke-width="1.7"/><line x1="5.1" y1="12.9" x2="12.9" y2="5.1" stroke="${C.stop}" stroke-width="1.7"/>`);
  return w(`<circle cx="9" cy="9" r="5.8" stroke="${C.ask}" stroke-width="1.5"/><circle cx="9" cy="9" r="1.9" fill="${C.ask}"/>`);
};

const statusColor = { working: C.pos, pending: "oklch(0.55 0.02 80)", failed: C.neg, stopped: C.stop };

const chev = (up = false) =>
  `<svg width="12" height="12" viewBox="0 0 12 12" fill="none" style="flex-shrink: 0; margin-top: 4px;" aria-hidden="true"><path d="${up ? "M3 7.5 L6 4.5 L9 7.5" : "M3 4.5 L6 7.5 L9 4.5"}" stroke="${C.faint}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

/* one service row inside the sidebar */
const svc = ({ state, name, status, proof, checked, detail = "", expanded = false, expandable = true, last = false }) => `
        <div style="border-bottom: ${last ? "none" : `1px solid ${C.line}`}; ${expanded ? `background: ${C.paper};` : ""}">
          <div class="tap" style="padding: 14px 22px; display: flex; gap: 11px; align-items: flex-start;">
            ${glyph(state, state === "pending" ? "pulse" : "")}
            <div style="display: flex; flex-direction: column; gap: 3px; flex-grow: 1; min-width: 0;">
              <div style="display: flex; align-items: baseline; gap: 10px;">
                <span style="font-family: ${SANS}; font-size: 14px; font-weight: 600; flex-grow: 1; ${state === "pending" ? `color: ${C.muted};` : ""}">${name}</span>
                <span style="font-family: ${SANS}; font-size: 12px; color: ${statusColor[state] || C.faint};">${status}</span>
              </div>
              ${proof ? `<div style="font-family: ${SERIF}; font-weight: 300; font-size: 14.5px; line-height: 1.45; color: ${C.muted};">${proof}</div>` : ""}
              ${checked ? `<div style="font-family: ${SANS}; font-size: 11.5px; color: ${C.faint};">${checked}</div>` : ""}
            </div>
            ${expandable ? chev(expanded) : ""}
          </div>
          ${detail ? `<div style="padding: 2px 22px 20px 49px; display: flex; flex-direction: column; gap: 18px;">${detail}</div>` : ""}
        </div>`;

const block = (title, inner) => `
            <div style="display: flex; flex-direction: column; gap: 7px;">
              <div style="font-family: ${SANS}; font-size: 11.5px; font-weight: 600; color: ${C.faint};">${title}</div>
              ${inner}
            </div>`;

const para = (t) => `<div style="font-family: ${SERIF}; font-weight: 300; font-size: 14.5px; line-height: 1.5; color: ${C.ink};">${t}</div>`;

const tick = (text, when) => `
              <div style="display: flex; align-items: baseline; gap: 8px;">
                <svg width="11" height="11" viewBox="0 0 12 12" fill="none" style="flex-shrink: 0;" aria-hidden="true"><path d="M2.4 6.2 L4.8 8.6 L9.6 3.4" stroke="${C.pos}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></svg>
                <span style="font-family: ${SERIF}; font-weight: 300; font-size: 14px; color: ${C.ink}; flex-grow: 1;">${text}</span>
                <span style="font-family: ${SANS}; font-size: 11px; color: ${C.faint};">${when}</span>
              </div>`;

const hist = (what, when, note = "") => `
              <div style="display: flex; align-items: baseline; gap: 8px;">
                <span style="font-family: ${SERIF}; font-weight: 300; font-size: 14px; color: ${C.muted}; flex-grow: 1;">${what}${note ? ` <span style="color: ${C.faint};">— ${note}</span>` : ""}</span>
                <span style="font-family: ${SANS}; font-size: 11px; color: ${C.faint};">${when}</span>
              </div>`;

const step = (text, when = "") => `
              <div style="display: flex; align-items: baseline; gap: 8px;">
                <span style="font-family: ${SERIF}; font-weight: 300; font-size: 14px; color: ${C.ink}; flex-grow: 1;">${text}</span>
                <span style="font-family: ${SANS}; font-size: 11px; color: ${C.faint};">${when}</span>
              </div>`;

const btn = (label, kind = "ghost", small = false) => {
  const pad = small ? "8px 14px" : "11px 20px";
  const fs = small ? "12.5px" : "13.5px";
  return kind === "solid"
    ? `<button class="btn btn-solid" style="font-family: ${SANS}; font-size: ${fs}; font-weight: 600; padding: ${pad}; background: ${C.ink}; color: ${C.paper}; border: none; border-radius: 3px;">${label}</button>`
    : `<button class="btn btn-ghost" style="font-family: ${SANS}; font-size: ${fs}; font-weight: 600; padding: ${pad}; background: ${C.paper}; color: ${C.ink}; border: 1px solid ${C.line2}; border-radius: 3px;">${label}</button>`;
};

const chatPad = (inner, pad = "40px 48px") => `
      <div style="flex-grow: 1; padding: ${pad}; display: flex; flex-direction: column; min-height: 0;">${inner}</div>`;

const ask = (text, size = 21) => `
        <div style="display: flex; gap: 16px; align-items: flex-start;">
          <span style="font-family: ${SANS}; font-size: 11.5px; color: ${C.faint}; padding-top: 6px; flex-shrink: 0;">you</span>
          <div style="font-family: ${SERIF}; font-weight: 300; font-size: ${size}px; line-height: 1.4; max-width: 460px; color: ${C.muted};">${text}</div>
        </div>`;

const composer = (placeholder = "Ask for something else…") => `
      <div style="flex-shrink: 0; border-top: 1px solid ${C.line}; padding: 16px 48px 20px;">
        <div style="display: flex; align-items: center; gap: 10px; border: 1px solid ${C.line2}; border-radius: 4px; padding: 12px 14px; background: ${C.paper};">
          <span style="font-family: ${SERIF}; font-size: 16px; color: oklch(0.72 0.008 70); flex-grow: 1;">${placeholder}</span>
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true"><path d="M8 13V3M8 3L4 7M8 3l4 4" stroke="${C.line2}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>
        </div>
      </div>`;

const emptySide = `
      <div style="flex-shrink: 0; padding: 20px 22px 14px;">
        <span style="font-family: ${SANS}; font-size: 13.5px; font-weight: 600;">Your product</span>
      </div>
      <div style="flex-grow: 1; padding: 6px 22px; display: flex; flex-direction: column; gap: 10px;">
        <div style="font-family: ${SERIF}; font-weight: 300; font-size: 15px; color: ${C.muted};">Nothing set up yet.</div>
        <div style="font-family: ${SERIF}; font-weight: 300; font-size: 15px; line-height: 1.5; color: ${C.faint}; max-width: 300px;">Whatever you ask for will show up here, with a note of what was actually checked.</div>
      </div>`;

const files = {};

/* ── 1 first launch ───────────────────────────── */
files["Empty.dc.html"] = shell(`${header("New product")}
${panes(
  chatPad(`
        <div style="flex-grow: 1; display: flex; flex-direction: column; justify-content: center; gap: 32px;">
          <h1 style="margin: 0; font-family: ${SERIF}; font-weight: 300; font-size: 34px; line-height: 1.2; letter-spacing: -0.015em; max-width: 460px;">What do you need your product to do?</h1>
          <div style="display: flex; flex-direction: column; gap: 11px;">
            <div style="font-family: ${SANS}; font-size: 12px; color: ${C.faint};">for example</div>
            ${["I need users to be able to sign up and log in", "users should be able to upload a profile photo", "when someone uploads a photo, email them a confirmation"]
              .map(t => `<div style="font-family: ${SERIF}; font-style: italic; font-weight: 300; font-size: 16.5px; color: ${C.muted};">&ldquo;${t}&rdquo;</div>`).join("\n            ")}
          </div>
        </div>`) + composer("Tell me what you're building…"),
  emptySide
)}`);

/* ── 2 thinking ───────────────────────────────── */
files["Thinking.dc.html"] = shell(`${header()}
${panes(
  chatPad(`
        <div style="display: flex; flex-direction: column; gap: 32px;">
          ${ask("when someone uploads a photo, email them a confirmation", 23)}
          <div style="display: flex; gap: 12px; align-items: center; padding-left: 40px;">
            ${glyph("pending", "pulse", 0)}
            <span style="font-family: ${SERIF}; font-size: 18px; font-weight: 300; color: ${C.muted};">working out what you'll need</span>
          </div>
        </div>`) + composer(),
  emptySide
)}`);

/* ── 3 checklist ──────────────────────────────── */
const cb = (on) => on
  ? `<svg width="16" height="16" viewBox="0 0 17 17" fill="none" style="flex-shrink: 0;" aria-hidden="true"><rect x="0.8" y="0.8" width="15.4" height="15.4" rx="3" fill="${C.ink}"/><path d="M4.8 8.7 L7.2 11.1 L12.2 6" stroke="${C.paper}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>`
  : `<svg width="16" height="16" viewBox="0 0 17 17" fill="none" style="flex-shrink: 0;" aria-hidden="true"><rect x="0.85" y="0.85" width="15.3" height="15.3" rx="3" stroke="${C.line2}" stroke-width="1.4"/></svg>`;

files["Checklist.dc.html"] = shell(`${header()}
${panes(
  chatPad(`
        <div style="display: flex; flex-direction: column; gap: 30px;">
          ${ask("when someone uploads a photo, email them a confirmation", 19)}
          <div style="display: flex; flex-direction: column; gap: 20px; padding-left: 40px;">
            <div style="font-family: ${SERIF}; font-weight: 300; font-size: 22px; letter-spacing: -0.01em;">Here's what I'll set up for that:</div>
            <div style="display: flex; flex-direction: column; gap: 2px; margin-left: -10px;">
              ${["a place to store photos", "something to resize them", "a way to send email"].map(t => `
              <div class="tap" style="display: flex; gap: 13px; align-items: center; padding: 10px; border-radius: 3px;">
                ${cb(true)}<span style="font-family: ${SERIF}; font-size: 18px;">${t}</span>
              </div>`).join("")}
            </div>
            <div style="display: flex; align-items: center; gap: 16px;">
              ${btn("set these up", "solid")}
              <span style="font-family: ${SANS}; font-size: 12px; color: ${C.faint};">uncheck anything you didn't ask for</span>
            </div>
          </div>
        </div>`) + composer(),
  emptySide
)}`);

/* ── 4 provisioning ───────────────────────────── */
files["Provisioning.dc.html"] = shell(`${header()}
${panes(
  chatPad(`
        <div style="display: flex; flex-direction: column; gap: 24px;">
          ${ask("when someone uploads a photo, email them a confirmation", 19)}
          <div style="font-family: ${SERIF}; font-weight: 300; font-size: 20px; padding-left: 40px;">Setting that up now.</div>
        </div>`) + composer(),
  sidebar(
    svc({ state: "working", name: "photo storage", status: "working", proof: "stored a test file, read it back unchanged", checked: "last checked 12s ago" }) +
    svc({ state: "pending", name: "something to resize them", status: "setting up…" }) +
    svc({ state: "pending", name: "a way to send email", status: "setting up…", last: true }),
    { count: "1 of 3 ready" })
)}`);

/* ── 5 all working ────────────────────────────── */
files["AllWorking.dc.html"] = shell(`${header()}
${panes(
  chatPad(`
        <div style="display: flex; flex-direction: column; gap: 22px;">
          ${ask("when someone uploads a photo, email them a confirmation", 19)}
          <div style="font-family: ${SERIF}; font-weight: 300; font-size: 20px; padding-left: 40px; color: ${C.muted};">All three are set up and checked.</div>
        </div>`) + composer(),
  sidebar(
    svc({ state: "working", name: "photo storage", status: "working", proof: "stored a test file, read it back unchanged", checked: "last checked 12s ago" }) +
    svc({ state: "working", name: "accounts", status: "working", proof: "created a test account, signed in as them", checked: "last checked 1m ago" }) +
    svc({ state: "working", name: "a way to send email", status: "working", proof: "sent a test email and confirmed it went out", checked: "last checked 1m ago", last: true }),
    { count: "3 working" })
)}`);

/* ── 6 partial failure (Main) ─────────────────── */
files["Main.dc.html"] = shell(`${header()}
${panes(
  chatPad(`
        <div style="display: flex; flex-direction: column; gap: 24px;">
          ${ask("when someone uploads a photo, email them a confirmation", 19)}
          <div style="display: flex; flex-direction: column; gap: 12px; padding-left: 40px; max-width: 420px;">
            <div style="font-family: ${SERIF}; font-weight: 300; font-size: 20px; line-height: 1.45;">Two of the three are working. Email isn't — I'm not going to tell you it is.</div>
            <div style="font-family: ${SERIF}; font-weight: 300; font-size: 16.5px; line-height: 1.5; color: ${C.muted};">You can try it again, or send the details to someone technical.</div>
          </div>
        </div>`) + composer(),
  sidebar(
    svc({ state: "working", name: "photo storage", status: "working", proof: "stored a test file, read it back unchanged", checked: "last checked 2m ago" }) +
    svc({ state: "working", name: "accounts", status: "working", proof: "created a test account, signed in as them", checked: "last checked 2m ago" }) +
    svc({
      state: "failed", name: "email", status: "not working yet",
      proof: "nothing arrived when I sent a test", checked: "tried twice",
      detail: `<div style="display: flex; gap: 8px;">${btn("try again", "ghost", true)}${btn("get help", "ghost", true)}</div>`,
      last: true
    }),
    { count: "2 of 3 working" })
)}`);

/* ── 7 escalated ──────────────────────────────── */
files["Escalated.dc.html"] = shell(`${header()}
${panes(
  chatPad(`
        <div style="display: flex; flex-direction: column; gap: 14px; max-width: 430px;">
          <div style="font-family: ${SERIF}; font-weight: 300; font-size: 20px; line-height: 1.45;">I tried twice and it still isn't working. I've stopped rather than keep guessing.</div>
          <div style="font-family: ${SERIF}; font-weight: 300; font-size: 16.5px; line-height: 1.5; color: ${C.muted};">Everything else is still fine. This one needs someone technical to look at it.</div>
        </div>`) + composer(),
  sidebar(
    svc({ state: "working", name: "photo storage", status: "working", proof: "stored a test file, read it back unchanged", checked: "last checked 4m ago" }) +
    svc({ state: "working", name: "accounts", status: "working", proof: "created a test account, signed in as them", checked: "last checked 4m ago" }) +
    svc({
      state: "stopped", name: "email", status: "stopped",
      proof: "needs a person — I've stopped trying", checked: "2 attempts, 2:31pm and 2:32pm",
      detail: `<div style="display: flex; gap: 8px;">${btn("get help", "ghost", true)}${btn("remove", "ghost", true)}</div>`,
      last: true
    }),
    { count: "2 working, 1 stopped" })
)}`);

/* ── 8 question ───────────────────────────────── */
files["Question.dc.html"] = shell(`${header()}
${panes(
  chatPad(`
        <div style="display: flex; flex-direction: column; gap: 30px;">
          ${ask("I need real-time chat between users", 20)}
          <div style="display: flex; gap: 13px; align-items: flex-start; padding-left: 40px;">
            ${glyph("ask", "", 8)}
            <div style="display: flex; flex-direction: column; gap: 20px;">
              <div style="font-family: ${SERIF}; font-weight: 300; font-size: 22px; line-height: 1.45; letter-spacing: -0.01em; max-width: 420px;">I can give you a place to store and look up messages, but not live chat yet.</div>
              <div style="display: flex; gap: 10px;">${btn("that works", "solid")}${btn("no, I need live chat")}</div>
            </div>
          </div>
        </div>`) + composer(),
  sidebar(
    svc({ state: "working", name: "photo storage", status: "working", proof: "stored a test file, read it back unchanged", checked: "last checked 5m ago" }) +
    svc({ state: "working", name: "accounts", status: "working", proof: "created a test account, signed in as them", checked: "last checked 5m ago", last: true }),
    { count: "2 working" })
)}`);

/* ── 9 returning ──────────────────────────────── */
files["Returning.dc.html"] = shell(`${header()}
${panes(
  chatPad(`
        <div style="display: flex; flex-direction: column; gap: 14px; max-width: 430px;">
          <div style="font-family: ${SERIF}; font-weight: 300; font-size: 20px; line-height: 1.45;">Welcome back. Let me check everything is still working before I show you anything.</div>
          <div style="font-family: ${SERIF}; font-weight: 300; font-size: 16.5px; line-height: 1.5; color: ${C.muted};">One of them stopped while you were away — I've marked it rather than leaving it looking fine.</div>
        </div>`) + composer(),
  sidebar(
    svc({ state: "pending", name: "photo storage", status: "checking…", proof: "checking it's still working…", expandable: false }) +
    svc({ state: "working", name: "a way to send email", status: "working", proof: "sent a test email and confirmed it went out", checked: "last checked just now" }) +
    svc({ state: "failed", name: "accounts", status: "not working yet", proof: "this stopped working since you were last here", detail: `<div style="display: flex; gap: 8px;">${btn("set it up again", "ghost", true)}${btn("get help", "ghost", true)}</div>`, last: true }),
    { count: "re-checking" })
)}`);

/* ── 10 expanded working ──────────────────────── */
files["ExpandedWorking.dc.html"] = shell(`${header()}
${panes(
  chatPad(`
        <div style="display: flex; flex-direction: column; gap: 14px; max-width: 430px;">
          <div style="font-family: ${SERIF}; font-weight: 300; font-size: 20px; line-height: 1.45; color: ${C.muted};">All three are set up and checked.</div>
        </div>`) + composer(),
  sidebar(
    svc({
      state: "working", name: "photo storage", status: "working", expanded: true,
      proof: "stored a test file, read it back unchanged", checked: "last checked 12s ago",
      detail:
        block("What this gives you", para("A place to keep photos people upload, and get them back later.")) +
        block("What I checked", tick("put a test file in", "12s ago") + tick("read it back, unchanged", "12s ago") + tick("removed the test file", "12s ago")) +
        block("History", hist("set up", "2:14pm") + hist("checked", "2:16pm", "worked") + hist("checked", "2:31pm", "worked")) +
        `<div style="display: flex; gap: 8px;">${btn("check it again", "ghost", true)}${btn("remove", "ghost", true)}</div>`
    }) +
    svc({ state: "working", name: "accounts", status: "working", proof: "created a test account, signed in as them", checked: "last checked 1m ago" }) +
    svc({ state: "working", name: "a way to send email", status: "working", proof: "sent a test email and confirmed it went out", checked: "last checked 1m ago", last: true }),
    { count: "3 working" })
)}`);

/* ── 11 expanded failure ──────────────────────── */
files["ExpandedFailure.dc.html"] = shell(`${header()}
${panes(
  chatPad(`
        <div style="display: flex; flex-direction: column; gap: 14px; max-width: 430px;">
          <div style="font-family: ${SERIF}; font-weight: 300; font-size: 20px; line-height: 1.45;">Two of the three are working. Email isn't — I'm not going to tell you it is.</div>
          <div style="font-family: ${SERIF}; font-weight: 300; font-size: 16.5px; line-height: 1.5; color: ${C.muted};">You can try it again, rebuild it from scratch, or send the details to someone technical.</div>
        </div>`) + composer(),
  sidebar(
    svc({ state: "working", name: "photo storage", status: "working", proof: "stored a test file, read it back unchanged", checked: "last checked 2m ago" }) +
    svc({
      state: "failed", name: "email", status: "not working yet", expanded: true,
      proof: "nothing arrived when I sent a test", checked: "tried twice",
      detail:
        block("What this would give you", para("A way to send email to your users — confirmations, welcome messages.")) +
        block("What I tried", step("sent a test message", "2:31pm") + step("waited 30 seconds") + step("nothing arrived") + `<div style="height: 5px;"></div>` + step("set it up again from scratch", "2:32pm") + step("sent another test — nothing arrived")) +
        `<div style="display: flex; gap: 8px; flex-wrap: wrap;">${btn("try again", "solid", true)}${btn("set it up fresh", "ghost", true)}${btn("get help", "ghost", true)}</div>`,
      last: true
    }),
    { count: "1 of 2 working" })
)}`);

/* ── 12 developer panel (modal) ───────────────── */
const devRow = (k, v) => `
          <div style="display: flex; gap: 16px; align-items: baseline;">
            <span style="font-family: ${SANS}; font-size: 11.5px; color: ${C.faint}; width: 80px; flex-shrink: 0;">${k}</span>
            <span style="font-family: ${SANS}; font-size: 12.5px; color: ${C.ink}; letter-spacing: 0.005em;">${v}</span>
          </div>`;

files["DeveloperPanel.dc.html"] = shell(`${header()}
${panes(
  chatPad(`
        <div style="display: flex; flex-direction: column; gap: 14px; max-width: 430px;">
          <div style="font-family: ${SERIF}; font-weight: 300; font-size: 20px; line-height: 1.45; color: ${C.muted};">Two of the three are working. Email isn't.</div>
        </div>`) + composer(),
  sidebar(
    svc({ state: "working", name: "photo storage", status: "working", proof: "stored a test file, read it back unchanged", checked: "last checked 2m ago" }) +
    svc({ state: "failed", name: "email", status: "not working yet", proof: "nothing arrived when I sent a test", checked: "tried twice", last: true }),
    { count: "1 of 2 working" })
)}
  <div style="position: absolute; inset: 0; background: oklch(0.27 0.012 70 / 0.28); display: flex; align-items: center; justify-content: center;">
    <div style="width: 560px; background: ${C.paper}; border-radius: 6px; box-shadow: 0 18px 48px oklch(0.27 0.012 70 / 0.22); overflow: hidden;">
      <div style="padding: 26px 28px 20px; display: flex; flex-direction: column; gap: 10px;">
        <div style="font-family: ${SERIF}; font-weight: 300; font-size: 25px; letter-spacing: -0.01em;">Details for a developer</div>
        <div style="font-family: ${SERIF}; font-weight: 300; font-size: 15.5px; line-height: 1.5; color: ${C.muted};">You don't need to read this. If you have someone technical, send it to them — it's everything they'd need to look into the email problem.</div>
      </div>
      <div style="margin: 0 28px; border: 1px solid ${C.line}; border-radius: 4px; overflow: hidden;">
        <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 16px; border-bottom: 1px solid ${C.line}; background: ${C.panel};">
          <span style="font-family: ${SANS}; font-size: 12px; font-weight: 600; color: ${C.muted};">email · 2 attempts</span>
          ${btn("copy", "ghost", true)}
        </div>
        <div style="padding: 16px; display: flex; flex-direction: column; gap: 8px;">
          ${devRow("capability", "send-email")}
          ${devRow("service", "ses · floci 2.0.1")}
          ${devRow("endpoint", "http://localhost:4566")}
          ${devRow("check", "aws ses list-identities")}
          ${devRow("result", "exit 254 — could not connect")}
          ${devRow("attempts", "2:31pm, 2:32pm")}
        </div>
      </div>
      <div style="padding: 22px 28px 26px; display: flex; gap: 10px;">
        ${btn("copy and close", "solid")}${btn("close")}
      </div>
    </div>
  </div>`);

/* ── 13 switcher ──────────────────────────────── */
const prod = (name, sub, active = false) => `
      <div class="tap" style="display: flex; align-items: center; justify-content: space-between; gap: 24px; padding: 11px 13px; border-radius: 4px; ${active ? `background: ${C.hover};` : ""}">
        <span style="font-family: ${SANS}; font-size: 14px; font-weight: 600;">${name}</span>
        <span style="font-family: ${SANS}; font-size: 12px; color: ${C.faint};">${sub}</span>
      </div>`;

files["Switcher.dc.html"] = shell(`${header("Photo app", { open: true })}
${panes(
  chatPad(`
        <div style="display: flex; flex-direction: column; gap: 14px; max-width: 430px;">
          <div style="font-family: ${SERIF}; font-weight: 300; font-size: 20px; line-height: 1.45; color: ${C.muted};">All three are set up and checked.</div>
        </div>`) + composer(),
  sidebar(
    svc({ state: "working", name: "photo storage", status: "working", proof: "stored a test file, read it back unchanged", checked: "last checked 12s ago" }) +
    svc({ state: "working", name: "accounts", status: "working", proof: "created a test account, signed in as them", checked: "last checked 1m ago" }) +
    svc({ state: "working", name: "a way to send email", status: "working", proof: "sent a test email and confirmed it went out", checked: "last checked 1m ago", last: true }),
    { count: "3 working" })
)}
  <div style="position: absolute; top: 52px; left: 16px; width: 320px; background: ${C.paper}; border: 1px solid ${C.line}; border-radius: 5px; box-shadow: 0 8px 28px oklch(0.27 0.012 70 / 0.12); padding: 7px; display: flex; flex-direction: column; gap: 2px;">
    ${prod("Photo app", "3 working", true)}
    ${prod("Recipe box", "1 working")}
    ${prod("Client portal", "nothing yet")}
    <div style="height: 1px; background: ${C.line}; margin: 6px 5px;"></div>
    <div class="tap" style="display: flex; align-items: center; gap: 9px; padding: 11px 13px; border-radius: 4px;">
      <svg width="13" height="13" viewBox="0 0 14 14" fill="none" aria-hidden="true"><path d="M7 2.4v9.2M2.4 7h9.2" stroke="${C.muted}" stroke-width="1.6" stroke-linecap="round"/></svg>
      <span style="font-family: ${SANS}; font-size: 13.5px; font-weight: 600; color: ${C.muted};">Start something new</span>
    </div>
  </div>`);


/* ══ export ═══════════════════════════════════ */

const node = (label, sub = "", tone = "ink") => `
        <div style="flex-shrink: 0; min-width: 128px; border: 1px solid ${tone === "soft" ? C.line2 : C.ink}; border-radius: 4px; padding: 12px 14px; background: ${C.paper}; display: flex; flex-direction: column; gap: 3px; align-items: center; text-align: center;">
          <span style="font-family: ${SANS}; font-size: 12.5px; font-weight: 600; color: ${tone === "soft" ? C.muted : C.ink};">${label}</span>
          ${sub ? `<span style="font-family: ${SANS}; font-size: 10.5px; color: ${C.faint};">${sub}</span>` : ""}
        </div>`;

const arrow = () => `
        <svg width="34" height="12" viewBox="0 0 34 12" fill="none" style="flex-shrink: 0;" aria-hidden="true"><path d="M0 6h28M24 2.4 28 6l-4 3.6" stroke="${C.line2}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/></svg>`;

const flow = (nodes) => `
      <div style="display: flex; align-items: center; justify-content: center; gap: 0; flex-wrap: nowrap;">${nodes.join(arrow())}</div>`;

const docPage = (inner) => `
  <div style="flex-grow: 1; background: oklch(0.955 0.004 85); padding: 34px 0; display: flex; justify-content: center; overflow: hidden;">
    <div style="width: 760px; background: ${C.paper}; border: 1px solid ${C.line}; box-shadow: 0 2px 14px oklch(0.27 0.012 70 / 0.06); padding: 44px 56px; display: flex; flex-direction: column; gap: 30px;">${inner}</div>
  </div>`;

const docHead = (title, sub) => `
      <div style="display: flex; flex-direction: column; gap: 6px; border-bottom: 1px solid ${C.line}; padding-bottom: 20px;">
        <div style="font-family: ${SERIF}; font-weight: 300; font-size: 28px; letter-spacing: -0.015em;">${title}</div>
        <div style="font-family: ${SANS}; font-size: 12.5px; color: ${C.faint};">${sub}</div>
      </div>`;

const docSection = (title, inner) => `
      <div style="display: flex; flex-direction: column; gap: 14px;">
        <div style="font-family: ${SANS}; font-size: 12px; font-weight: 600; color: ${C.faint};">${title}</div>
        ${inner}
      </div>`;

const docItem = (state, name, proof, when) => `
        <div style="display: flex; gap: 11px; align-items: flex-start;">
          ${glyph(state)}
          <div style="display: flex; flex-direction: column; gap: 2px; flex-grow: 1;">
            <div style="display: flex; align-items: baseline; gap: 10px;">
              <span style="font-family: ${SANS}; font-size: 13.5px; font-weight: 600; flex-grow: 1;">${name}</span>
              <span style="font-family: ${SANS}; font-size: 11.5px; color: ${statusColor[state]};">${state === "working" ? "working" : "not working yet"}</span>
            </div>
            <div style="font-family: ${SERIF}; font-weight: 300; font-size: 14.5px; color: ${C.muted};">${proof}</div>
            <div style="font-family: ${SANS}; font-size: 11px; color: ${C.faint};">${when}</div>
          </div>
        </div>`;

/* ── 14 export dialog ─────────────────────────── */
const optRow = (checked, label, sub) => `
          <div class="tap" style="display: flex; gap: 12px; align-items: flex-start; padding: 10px; border-radius: 3px;">
            ${cb(checked)}
            <div style="display: flex; flex-direction: column; gap: 2px;">
              <span style="font-family: ${SANS}; font-size: 13.5px; font-weight: 600; ${checked ? "" : `color: ${C.muted};`}">${label}</span>
              <span style="font-family: ${SERIF}; font-weight: 300; font-size: 14px; color: ${C.faint};">${sub}</span>
            </div>
          </div>`;

const radioRow = (on, label, sub) => `
          <div class="tap" style="display: flex; gap: 12px; align-items: flex-start; padding: 10px; border-radius: 3px;">
            <svg width="16" height="16" viewBox="0 0 17 17" fill="none" style="flex-shrink: 0; margin-top: 1px;" aria-hidden="true"><circle cx="8.5" cy="8.5" r="7.6" stroke="${on ? C.ink : C.line2}" stroke-width="1.4"/>${on ? `<circle cx="8.5" cy="8.5" r="4" fill="${C.ink}"/>` : ""}</svg>
            <div style="display: flex; flex-direction: column; gap: 2px;">
              <span style="font-family: ${SANS}; font-size: 13.5px; font-weight: 600; ${on ? "" : `color: ${C.muted};`}">${label}</span>
              <span style="font-family: ${SERIF}; font-weight: 300; font-size: 14px; color: ${C.faint};">${sub}</span>
            </div>
          </div>`;

files["Export.dc.html"] = shell(`${header()}
${panes(
  chatPad(`<div style="font-family: ${SERIF}; font-weight: 300; font-size: 20px; color: ${C.muted};">All three are set up and checked.</div>`) + composer(),
  sidebar(
    svc({ state: "working", name: "photo storage", status: "working", proof: "stored a test file, read it back unchanged", checked: "last checked 12s ago" }) +
    svc({ state: "working", name: "accounts", status: "working", proof: "created a test account, signed in as them", checked: "last checked 1m ago", last: true }),
    { count: "3 working" })
)}
  <div style="position: absolute; inset: 0; background: oklch(0.27 0.012 70 / 0.28); display: flex; align-items: center; justify-content: center;">
    <div style="width: 620px; background: ${C.paper}; border-radius: 6px; box-shadow: 0 18px 48px oklch(0.27 0.012 70 / 0.22); overflow: hidden;">
      <div style="padding: 26px 28px 4px; display: flex; flex-direction: column; gap: 8px;">
        <div style="font-family: ${SERIF}; font-weight: 300; font-size: 25px; letter-spacing: -0.01em;">Export what you have</div>
        <div style="font-family: ${SERIF}; font-weight: 300; font-size: 15.5px; line-height: 1.5; color: ${C.muted};">A record of what your product runs on, and what was actually checked.</div>
      </div>
      <div style="display: flex; gap: 0; padding: 18px 20px 4px;">
        <div style="flex: 1; display: flex; flex-direction: column; gap: 2px;">
          <div style="font-family: ${SANS}; font-size: 11.5px; font-weight: 600; color: ${C.faint}; padding: 0 10px 6px;">What goes in</div>
          ${optRow(true, "What your product has", "the list, in plain words")}
          ${optRow(true, "How the pieces fit together", "a diagram")}
          ${optRow(true, "What was checked, and when", "the proof")}
          ${optRow(false, "Technical details", "for a developer")}
        </div>
        <div style="width: 1px; background: ${C.line}; margin: 0 14px;"></div>
        <div style="flex: 1; display: flex; flex-direction: column; gap: 2px;">
          <div style="font-family: ${SANS}; font-size: 11.5px; font-weight: 600; color: ${C.faint}; padding: 0 10px 6px;">As</div>
          ${radioRow(true, "A page to share", "PDF — send it to anyone")}
          ${radioRow(false, "Just the diagram", "an image")}
          ${radioRow(false, "A written summary", "text you can paste anywhere")}
          ${radioRow(false, "Files a developer needs", "a folder they can run")}
        </div>
      </div>
      <div style="padding: 20px 28px 26px; display: flex; gap: 10px; align-items: center;">
        ${btn("Export", "solid")}${btn("Cancel")}
        <span style="font-family: ${SANS}; font-size: 11.5px; color: ${C.faint}; margin-left: auto;">nothing leaves your machine</span>
      </div>
    </div>
  </div>`);

/* ── 15 the exported page, plain ──────────────── */
files["ExportPlain.dc.html"] = shell(`${header()}
${docPage(`
      ${docHead("Photo app", "What this product runs on · 6 September 2026")}
      ${docSection("How it fits together", flow([
        node("someone uploads<br>a photo", "", "soft"),
        node("photo storage"),
        node("resizing"),
        node("a confirmation<br>email"),
      ]))}
      ${docSection("What your product has",
        `<div style="display: flex; flex-direction: column; gap: 16px;">` +
        docItem("working", "photo storage", "stored a test file, read it back unchanged", "checked 6 Sep, 2:31pm") +
        docItem("working", "accounts", "created a test account, signed in as them", "checked 6 Sep, 2:31pm") +
        docItem("working", "a way to send email", "sent a test email and confirmed it went out", "checked 6 Sep, 2:31pm") +
        `</div>`)}
      ${docSection("Worth knowing",
        `<div style="font-family: ${SERIF}; font-weight: 300; font-size: 15px; line-height: 1.6; color: ${C.muted}; max-width: 560px;">All of this runs on your own machine. Nothing here is live on the internet yet, and nobody outside your computer can reach it.</div>`)}`)}`);

/* ── 16 the exported page, technical ──────────── */
const techRow = (a, b, c) => `
          <div style="display: flex; gap: 16px; align-items: baseline; padding: 7px 0; border-bottom: 1px solid ${C.line};">
            <span style="font-family: ${SANS}; font-size: 12.5px; font-weight: 600; width: 150px; flex-shrink: 0;">${a}</span>
            <span style="font-family: ${SANS}; font-size: 12.5px; color: ${C.ink}; flex-grow: 1;">${b}</span>
            <span style="font-family: ${SANS}; font-size: 12px; color: ${C.faint};">${c}</span>
          </div>`;

files["ExportTechnical.dc.html"] = shell(`${header()}
${docPage(`
      ${docHead("Photo app — technical summary", "Verified against floci 2.0.1 · 6 September 2026, 2:31pm")}
      ${docSection("Architecture", flow([
        node("client", "app", "soft"),
        node("s3", "photoapp-uploads"),
        node("lambda", "photoapp-resize"),
        node("ses", "confirmations"),
      ]))}
      ${docSection("Resources",
        `<div style="display: flex; flex-direction: column;">
          <div style="display: flex; gap: 16px; align-items: baseline; padding-bottom: 7px; border-bottom: 1px solid ${C.line2};">
            <span style="font-family: ${SANS}; font-size: 11px; color: ${C.faint}; width: 150px; flex-shrink: 0;">capability</span>
            <span style="font-family: ${SANS}; font-size: 11px; color: ${C.faint}; flex-grow: 1;">resource</span>
            <span style="font-family: ${SANS}; font-size: 11px; color: ${C.faint};">verified by</span>
          </div>` +
          techRow("file-storage", "s3 · photoapp-uploads", "put + get roundtrip") +
          techRow("user-accounts", "cognito-idp · photoapp-users", "signup + auth") +
          techRow("background-job", "lambda · photoapp-resize", "invoke, exit 0") +
          techRow("send-email", "ses · verified sender", "send + delivery log") +
        `</div>`)}
      ${docSection("Included in this export",
        `<div style="font-family: ${SANS}; font-size: 12.5px; line-height: 2; color: ${C.muted};">docker-compose.yml<br>.env<br>endpoints.json<br>stack-plan.json<br>verification.md</div>`)}`)}`);

for (const [name, content] of Object.entries(files)) writeFileSync(name, content);
console.log("wrote", Object.keys(files).length, "artboards");
