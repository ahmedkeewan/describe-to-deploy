# Design Brief — Founder Interface

> **Archived.** Superseded by [interface/regenerate-prompt.md](../../interface/regenerate-prompt.md)
> and [interface/README.md](../../interface/README.md). This first brief described nine stacked
> screens with no expandable rows. The design moved to sixteen screens in two panes, with rows
> that expand into more plain language. Kept for the record; don't design from it.

A brief for producing visual designs of the interface specified in
[interface/spec.md](../../interface/spec.md). Copy was taken verbatim from
[founder-copy.md](../../interface/founder-copy.md).

---

## What this product is

A non-technical founder writes what they need in plain English — *"I need users to be able to
upload photos"* — and the infrastructure that makes it possible is set up on their machine,
verified for real, and reported back in words they understand.

**The user cannot verify anything themselves.** They cannot read a log, judge a configuration, or
tell a working setup from a broken one. So the interface has one job beyond being usable: never
let them believe something works when it doesn't.

Every design decision below serves that.

## Tone

**Calm and plainly honest.** Closer to a doctor's report than a deployment dashboard.

- **No celebration on success.** No confetti, no "🎉 All set!", no green flooding the screen.
  Something working is the expected outcome, not an achievement.
- **No alarm on failure.** No red banners, no warning triangles, no shouting. A failure is
  reported the way a careful person reports one: state it, say what it means, offer the next
  step.
- **Quiet confidence, not marketing.** The founder is trusting this tool with something they
  cannot check. Enthusiasm reads as compensation.

The emotional register that fits: a knowledgeable friend telling you the truth about your car.

## Hard constraints

Violating any of these breaks the product's thesis, not just its style.

**Never appears anywhere on screen:**

```
  service names      S3, Cognito, DynamoDB, Lambda, SES, RDS, Redis
  infra nouns        bucket, table, instance, container, endpoint, port,
                     region, ARN, IAM, role, policy, queue, trigger
  protocol/format    JWT, CORS, presigned URL, API, SDK, JSON, YAML, env var
  ops verbs          provision, deploy, configure, spin up, boot, mount
  error surfaces     exit codes, stack traces, exception names
  file paths         .env, docker-compose.yml, ~/.aws/config
```

**Also never:**

- **Progress bars or percentages.** Nothing here has a knowable duration, and a stalled 80% is a
  lie. Indeterminate motion only.
- **"View details," "Show logs," "Learn more."** There is no second layer. The one visible
  sentence is the whole disclosure.
- **Tooltips or hover-only content.** Everything that matters is always visible.
- **Keyboard shortcuts or hidden panels.** Every affordance is a labelled button.
- **Clickable status rows.** They are statements, not navigation.
- **Time estimates or ETAs.**

**Always:**

- Every `working` row shows its proof sentence *and* "last checked N ago." Both, always visible.
- Exactly one primary action per failure.
- If any row is not working, the overall impression must not read as success.

## Layout

Two zones, fixed. Conversation above, board below.

```
┌──────────────────────────────────────────────┐
│                                              │
│   CONVERSATION                               │   ephemeral
│   what was asked, what's being done          │   scrolls
│                                              │
├──────────────────────────────────────────────┤
│                                              │
│   YOUR PRODUCT                               │   persistent
│   the durable list of capabilities           │   never scrolls away
│                                              │
└──────────────────────────────────────────────┘
```

The board is the anchor. It is the founder's answer to *"what do I have?"* and must be visible at
all times, including while the conversation is active.

## Status vocabulary

The complete set. Nothing else may appear as a status.

| Symbol | Label | Meaning |
|---|---|---|
| ◐ | `setting up…` | In progress. **Also covers "created but not yet proven."** |
| ● | `working` | Proven by a real check. Always with a proof sentence. |
| ○ | `not working yet` | The check ran and failed. |
| ⊘ | `stopped — needs a person` | Escalated after one retry. |
| ? | `waiting on your answer` | A question is open. |

**There is deliberately no status meaning "started but unverified."** Something created but
unproven stays `setting up…`. It never gets to look like success. Do not invent an intermediate
state, a "pending" style, or a hopeful colour for it.

Symbols above are placeholders for meaning, not a required visual language — but the five states
must remain visually distinguishable without relying on colour alone.

---

# The nine screens

Draw all nine. Screens 6–9 are where this product earns its thesis; a design that only shows the
happy path has missed the point.

---

## 1. Empty — first launch

Nothing has been asked yet. The board does not exist.

```
  What do you need your product to do?

  ▸ _

  for example:
    "I need users to be able to sign up and log in"
    "users should be able to upload a profile photo"
    "when someone uploads a photo, email them a confirmation"
```

Notes: the examples are the point — they teach the register without instructions. No onboarding,
no tour, no explanation of what the tool is.

## 2. Thinking

The request has been sent; the plan has not come back.

```
  you ▸ when someone uploads a photo,
        email them a confirmation

  ◐ working out what you'll need
```

Notes: indeterminate motion only. No percentage, no step counter, no "1 of 3."

## 3. Checklist — the confirmation gate

The single moment the founder decides anything. Everything arrives pre-checked.

```
  Here's what I'll set up for that:

    ☑ a place to store photos
    ☑ something to resize them
    ☑ a way to send email

    [ set these up ]
```

With a dependency unchecked:

```
    ☐ a place to store photos
    ☒ something to resize them
      this needs somewhere to put the photos first
```

Notes: this is the mechanism that prevents the agent from silently building more than was asked.
It should feel light — a confirmation, not a form. The founder cannot judge infrastructure, but
they can judge *"I never asked for email."*

## 4. Provisioning — a mixed board

The most common live state. Some rows proven, some still going.

```
  Setting that up now.

  ─────────────────────────────────
  YOUR PRODUCT

  ● photo storage       working
    stored a test file, read it back unchanged
    last checked 12s ago

  ◐ something to resize them
    setting up…

  ◐ a way to send email
    setting up…
```

Notes: rows in different states sit together without visual drama. A `setting up…` row must not
look like a problem.

## 5. All working

```
  YOUR PRODUCT

  ● photo storage       working
    stored a test file, read it back unchanged
    last checked 12s ago

  ● accounts            working
    created a test account, signed in as them
    last checked 1m ago

  ● a way to send email  working
    sent a test email and confirmed it went out
    last checked 1m ago
```

Notes: **no celebration.** No summary banner, no "All set!", no success illustration. The rows
speak for themselves. This restraint is deliberate and is the design's most likely point of
failure — resist the instinct to reward the user.

## 6. Partial failure — the honest one

The most important screen in the product.

```
  YOUR PRODUCT

  ● photo storage       working
    stored a test file, read it back unchanged
    last checked 2m ago

  ● accounts            working
    created a test account, signed in as them
    last checked 2m ago

  ○ email               not working yet
    nothing arrived when I sent a test

    Your photo storage still works — this
    one piece isn't ready.

    [ try again ]
```

Notes: the failing row carries a second sentence saying what still works — a founder needs both
halves. Exactly one action. **The screen overall must not read as success**, but must also not
read as catastrophe. Two of three things working is neither.

## 7. Escalated — the retry is spent

```
  ⊘ email               stopped — needs a person

    I tried twice and it still isn't working.
    I've stopped rather than keep guessing.

    Everything else is still fine.
```

Notes: no action button. This is a terminal state, and the design should feel settled rather than
stuck — the tool has made a decision, not given up mid-task.

## 8. Question — outside what's supported

The agent has hit something it does not know how to build, and asks rather than improvising.

```
  I can give you a place to store and look up
  messages, but not live chat yet.

  [ that works ]   [ no, I need live chat ]
```

Nothing close enough to offer:

```
  I can't set that up yet — it's not something
  I know how to do properly, and I'd rather say
  so than get it wrong.

  I've made a note of what you asked for.
```

Notes: this should read as competence, not limitation. The tool declining to guess is a feature
being demonstrated.

## 9. Returning — reconciling on startup

The founder reopens the tool. Existing rows are re-checked before any of them are shown as
working.

```
  YOUR PRODUCT

  ◐ photo storage
    checking it's still working…

  ◐ accounts
    checking it's still working…
```

Then resolving, with one that didn't survive:

```
  ● photo storage       working
    stored a test file, read it back unchanged
    last checked just now

  ○ accounts            not working yet
    this stopped working since you were last here
```

Notes: rows never render green from memory. This screen exists because a saved file describing
running services is a claim that goes stale, and the product's whole thesis is that claims must
be checked.

---

## Responsive

Desktop-first — this runs in a browser on the founder's laptop. A narrow layout should stack the
two zones rather than hiding the board; the board is never the thing that gets collapsed.

## What to produce

One artboard per screen, in the order above, on a single canvas. Screens 4–7 should be readable
side by side, since the difference between them is the entire design argument.
