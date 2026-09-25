# Regeneration Prompt

Paste everything between the rules into Claude Design (claude.ai/design) to rebuild the 16-screen
canvas from scratch. Self-contained — it does not depend on any other file in this repo.

> **Status:** this rebuilds the full 16-screen design. Part of it ships as the live board
> (`live.html`, started with `make board`), and the rest is design only. What founders mainly use
> is chat (Claude Desktop, Claude Code, Cursor) talking to the MCP server in
> [`harness/`](../harness/). See [README.md](README.md#status-whats-built-and-whats-design) for
> which parts are built.

---

Build a 16-artboard design canvas for a desktop web app called **Service Buddy**. Lay the
artboards out in a grid, three per row, in the numbered order below.

## What the product is

A non-technical founder writes what they need in plain English — "I need users to be able to
upload photos" — and the infrastructure that makes it possible is set up on their own machine,
verified for real, and reported back in words they understand. No cloud account, no deploy, no
code required.

**The one fact that drives every decision:** this user cannot verify anything themselves. They
cannot read a log, judge a configuration, or tell a working setup from a broken one. So the
interface has one job beyond being usable — never let them believe something works when it
doesn't.

## Tone

Calm and plainly honest. Closer to a doctor's report than a deployment dashboard.

- **No celebration on success.** No confetti, no "All set!", no banner, no success illustration.
  Something working is the expected outcome, not an achievement.
- **No alarm on failure.** No red, no warning triangles, no shouting. A failure is stated the way
  a careful person states one: what happened, what it means, what to do next.
- Quiet confidence, never marketing enthusiasm.

## Hard constraints

Never anywhere on screen (except where explicitly marked "for a developer"):

```
service names   S3, Cognito, DynamoDB, Lambda, SES, RDS, Redis
infra nouns     bucket, table, instance, container, endpoint, port, region, ARN, IAM
protocols       JWT, CORS, presigned URL, API, SDK, env var
ops verbs       provision, deploy, configure, spin up, boot
error surfaces  exit codes, stack traces, exception names
file paths      .env, docker-compose.yml
```

Also never: progress bars or percentages (nothing here has a knowable duration); time estimates;
tooltips or hover-only content; keyboard shortcuts; all-caps or monospace section headers; emoji.

Always: every "working" row shows both its proof sentence and "last checked N ago"; exactly one
primary action per failure; if anything is not working, the overall impression must not read as
success.

## Design system

**Fonts** (Google Fonts): `Newsreader` weight 300/400, including italic — used for everything the
product *says*, and for headings. `Karla` weight 400/500/600 — used for interface labels, names,
status words, buttons. Never Inter, Roboto, or Arial as the primary face.

**Color** (oklch, warm and low-chroma — do not substitute a status-page green/red/amber palette):

```
paper       oklch(0.987 0.003 85)     app background
panel       oklch(0.971 0.004 85)     sidebar background
ink         oklch(0.27 0.012 70)      primary text
muted       oklch(0.46 0.01 70)       secondary text
faint       oklch(0.58 0.008 70)      tertiary text, labels
line        oklch(0.905 0.005 80)     hairlines
line2       oklch(0.82 0.008 80)      button + input borders
positive    oklch(0.52 0.075 155)     working
negative    oklch(0.53 0.085 40)      not working yet
stopped     oklch(0.44 0.05 38)       stopped
pending     oklch(0.62 0.025 80)      setting up
asking      oklch(0.52 0.045 250)     waiting on an answer
hover       oklch(0.945 0.005 80)
```

No shadows except on modals and dropdowns. No gradients. No cards — separate things with
hairlines. Border radius 3–4px, never pill-shaped.

**Type scale**

```
page heading      Newsreader 300, 34px, line-height 1.2, letter-spacing -0.015em
doc heading       Newsreader 300, 28px
modal heading     Newsreader 300, 25px
agent voice       Newsreader 300, 20-23px, line-height 1.45
agent secondary   Newsreader 300, 16.5px, line-height 1.5
proof sentence    Newsreader 300, 14.5px, line-height 1.45, muted
examples          Newsreader 300 italic, 16.5px, muted
capability name   Karla 600, 14px
status word       Karla 400, 12px, in its status color
section label     Karla 600, 11.5-12px, faint — sentence case, never all-caps
timestamp         Karla 400, 11-11.5px, faint
button            Karla 600, 13.5px (12.5px for small)
```

## Layout skeleton — identical on every app screen

Artboard 1200 × 760.

```
┌──────────────────────────────────────────────────────────┐
│ header · 56px · bottom hairline                          │
│  [4-square mark] Photo app ⌄            [gear icon]      │
├────────────────────────────────┬─────────────────────────┤
│                                │ sidebar · 420px         │
│ conversation                   │ left hairline           │
│ flex-grow, padding 40px 48px   │ panel background        │
│                                │                         │
│                                │  Your product      3 …  │
│                                │  ─────────────────────  │
│                                │  capability rows,       │
│                                │  hairline between       │
├────────────────────────────────┤  ─────────────────────  │
│ composer · top hairline        │  ↓ Export what you have │
│ 1px box, placeholder text      │                         │
└────────────────────────────────┴─────────────────────────┘
```

The sidebar is permanent. It is never pushed off-screen by the conversation, and it is the
answer to "what do I have?"

## Components

**Header.** Left: a 15px four-square mark (two dark squares diagonal, two light), the product
name in Karla 600 14px, a small chevron. Right: a stroked gear icon, 16px, faint. Both sides are
hover-highlighted tap targets with 4px radius.

**Status glyphs** — 16px circles, drawn as SVG, distinguishable by *shape* not only color:

```
working       filled circle, positive
setting up…   outlined circle with the right half filled, pending, gently pulsing
                (2.4s ease-in-out opacity 0.35↔1; disable under prefers-reduced-motion)
not working   outlined circle only, 1.8px stroke, negative
stopped       outlined circle with a diagonal slash, stopped
waiting       outlined circle with a small centered dot, asking
```

There is deliberately **no glyph for "started but unverified."** Anything created but unproven
stays "setting up…". Do not invent an intermediate state.

**Capability row** (in the sidebar) — 14px 22px padding, bottom hairline, hover highlight:

```
[glyph]  capability name ──────────── status word    ⌄
         proof sentence, Newsreader, muted
         last checked N ago, Karla, faint
```

Expanding gives the row a paper background and reveals an indented detail area (left inset 49px)
containing sentence-case labelled blocks and a row of small buttons.

**Buttons.** Solid = ink background, paper text, no border. Ghost = paper background, ink text,
1px line2 border. Radius 3px. Padding 11px 20px (small: 8px 14px). Visible focus ring in the
negative color, 2px, 3px offset.

**Composer.** A 1px line2 box with 4px radius, greyed placeholder in Newsreader 16px, and a small
up-arrow icon on the right.

**Modal.** Centered over a `oklch(0.27 0.012 70 / 0.28)` scrim, paper background, 6px radius,
soft shadow.

**Diagram nodes.** Rounded rectangles, 1px ink border (soft variants use line2), centered Karla
600 12.5px label with an optional 10.5px faint sub-label, joined by thin right-arrows in line2.

---

# The sixteen screens

Copy is exact. Do not rewrite it.

### 1 · First launch
Header product name reads **New product**. Sidebar shows the empty state. Conversation is
vertically centered.

- Heading: **What do you need your product to do?**
- Label: `for example`
- Three italic lines: *"I need users to be able to sign up and log in"* / *"users should be able
  to upload a profile photo"* / *"when someone uploads a photo, email them a confirmation"*
- Composer placeholder: `Tell me what you're building…`
- Sidebar empty state: **Your product**, then *Nothing set up yet.* and *Whatever you ask for
  will show up here, with a note of what was actually checked.*

### 2 · Working it out
- `you` label + *when someone uploads a photo, email them a confirmation*
- Pulsing pending glyph + *working out what you'll need*
- Sidebar still empty.

### 3 · The confirmation gate
- The same `you` line, smaller.
- **Here's what I'll set up for that:** (Newsreader 22px)
- Three checked rows in Newsreader 18px: *a place to store photos* / *something to resize them* /
  *a way to send email*
- Solid button **set these up**, beside faint text *uncheck anything you didn't ask for*
- Sidebar still empty.

### 4 · Setting up
Conversation: the `you` line, then *Setting that up now.*
Sidebar count reads `1 of 3 ready`:
- working · **photo storage** · *stored a test file, read it back unchanged* · last checked 12s ago
- setting up… · **something to resize them**
- setting up… · **a way to send email**

### 5 · All working
Conversation: the `you` line, then *All three are set up and checked.*
Sidebar count `3 working`, three working rows:
- **photo storage** · *stored a test file, read it back unchanged* · last checked 12s ago
- **accounts** · *created a test account, signed in as them* · last checked 1m ago
- **a way to send email** · *sent a test email and confirmed it went out* · last checked 1m ago

### 6 · Partial failure — the most important screen
Conversation:
> **Two of the three are working. Email isn't — I'm not going to tell you it is.**
> *You can try it again, or send the details to someone technical.*

Sidebar count `2 of 3 working`: two working rows as above, then
- not working yet · **email** · *nothing arrived when I sent a test* · tried twice
- inside that row, two small ghost buttons: **try again**, **get help**

### 7 · Stopped — needs a person
Conversation:
> **I tried twice and it still isn't working. I've stopped rather than keep guessing.**
> *Everything else is still fine. This one needs someone technical to look at it.*

Sidebar count `2 working, 1 stopped`; third row uses the slashed glyph, status `stopped`, proof
*needs a person — I've stopped trying*, timestamp *2 attempts, 2:31pm and 2:32pm*, buttons
**get help** and **remove**.

### 8 · Outside what's supported
- `you` line: *I need real-time chat between users*
- Waiting glyph + **I can give you a place to store and look up messages, but not live chat yet.**
- Buttons: solid **that works**, ghost **no, I need live chat**
- Sidebar keeps two working rows.

### 9 · Coming back later
Conversation:
> **Welcome back. Let me check everything is still working before I show you anything.**
> *One of them stopped while you were away — I've marked it rather than leaving it looking fine.*

Sidebar count `re-checking`:
- setting up… · **photo storage** · *checking it's still working…* (no chevron)
- working · **a way to send email** · *sent a test email and confirmed it went out* · last checked just now
- not working yet · **accounts** · *this stopped working since you were last here* · buttons
  **set it up again**, **get help**

### 10 · Expanded — what was actually checked
Sidebar `3 working`, first row expanded, showing:
- `What this gives you` — *A place to keep photos people upload, and get them back later.*
- `What I checked` — three ticked lines with times: *put a test file in* (12s ago), *read it back,
  unchanged* (12s ago), *removed the test file* (12s ago)
- `History` — *set up* 2:14pm · *checked — worked* 2:16pm · *checked — worked* 2:31pm
- Buttons **check it again**, **remove**

### 11 · Expanded — what I tried, and what you can do
Conversation as screen 6, with the second line extended: *You can try it again, rebuild it from
scratch, or send the details to someone technical.*
Sidebar `1 of 2 working`, the email row expanded:
- `What this would give you` — *A way to send email to your users — confirmations, welcome messages.*
- `What I tried` — *sent a test message* 2:31pm · *waited 30 seconds* · *nothing arrived* ·
  (gap) · *set it up again from scratch* 2:32pm · *sent another test — nothing arrived*
- Buttons: solid **try again**, ghost **set it up fresh**, ghost **get help**

### 12 · Get help — the developer handoff
A modal over the app, 560px wide.
- Heading **Details for a developer**
- *You don't need to read this. If you have someone technical, send it to them — it's everything
  they'd need to look into the email problem.*
- A bordered box, header strip reads `email · 2 attempts` with a small **copy** button, then
  key/value rows in Karla (the only place jargon is allowed — still set in Karla, never monospace):
  `capability send-email` · `service ses · floci 2.0.1` · `endpoint http://localhost:4566` ·
  `check aws ses list-identities` · `result exit 254 — could not connect` ·
  `attempts 2:31pm, 2:32pm`
- Buttons: solid **copy and close**, ghost **close**

### 13 · Switching products
A dropdown open under the header, 320px, listing one row per product with a count on the right:
**Photo app** `3 working` (highlighted) · **Recipe box** `1 working` · **Client portal**
`nothing yet` · hairline · **+ Start something new**. The header's tap target is highlighted.

### 14 · Export
A modal, 620px, two columns split by a vertical hairline.
- Heading **Export what you have**, then *A record of what your product runs on, and what was
  actually checked.*
- Left column `What goes in` — checkboxes: ☑ **What your product has** *the list, in plain words* ·
  ☑ **How the pieces fit together** *a diagram* · ☑ **What was checked, and when** *the proof* ·
  ☐ **Technical details** *for a developer*
- Right column `As` — radios: ● **A page to share** *PDF — send it to anyone* · ○ **Just the
  diagram** *an image* · ○ **A written summary** *text you can paste anywhere* · ○ **Files a
  developer needs** *a folder they can run*
- Footer: solid **Export**, ghost **Cancel**, and right-aligned faint text *nothing leaves your
  machine*

### 15 · What you get — plain
Not an app screen: a 760px document page centered on a slightly darker ground, with a hairline
border and soft shadow.
- Title **Photo app**, subtitle `What this product runs on · 6 September 2026`
- `How it fits together` — a left-to-right diagram: *someone uploads a photo* (soft) →
  *photo storage* → *resizing* → *a confirmation email*
- `What your product has` — the three working rows with proof sentences and *checked 6 Sep, 2:31pm*
- `Worth knowing` — *All of this runs on your own machine. Nothing here is live on the internet
  yet, and nobody outside your computer can reach it.*

### 16 · What you get — technical
Same document format.
- Title **Photo app — technical summary**, subtitle `Verified against floci 2.0.1 · 6 September
  2026, 2:31pm`
- `Architecture` — diagram: *client / app* (soft) → *s3 / photoapp-uploads* → *lambda /
  photoapp-resize* → *ses / confirmations*
- `Resources` — a table with columns `capability`, `resource`, `verified by`:
  `file-storage` / `s3 · photoapp-uploads` / `put + get roundtrip` ·
  `user-accounts` / `cognito-idp · photoapp-users` / `signup + auth` ·
  `background-job` / `lambda · photoapp-resize` / `invoke, exit 0` ·
  `send-email` / `ses · verified sender` / `send + delivery log`
- `Included in this export` — a plain list in Karla: `docker-compose.yml`, `.env`, `endpoints.json`,
  `stack-plan.json`, `verification.md`

---

## Sticky notes to place beside the canvas

- Beside row 1 — **Two panes, fixed.** Left: the conversation, ephemeral. Right: Your product,
  the durable list of what exists, always visible, never pushed off screen by chat. Each row
  expands in place.
- Beside row 2 — **The design argument lives in screens 4–7.** There is deliberately no status
  meaning "started but unverified" — something created but unproven stays "setting up…". That
  missing state is why the verification gate can't be quietly downgraded later: there is nowhere
  in the UI to put a half-truth.
- Beside row 3 — **No celebration on success**, and no alarm on failure. This is the design's
  most likely point of failure: resist the instinct to reward the user.
- Beside row 4 — **"No jargon" and "no depth" are different rules.** A doctor's report has depth.
  Expanding a row reveals more plain language, never more jargon. Screen 12 is where technical
  detail lives, and it survives the rule because it is explicitly addressed to someone else.
- Beside row 6 — **Export is what the founder walks away with.** One checkbox switches audience:
  the plain page is what they send an investor, the technical one is what a developer picks up.
