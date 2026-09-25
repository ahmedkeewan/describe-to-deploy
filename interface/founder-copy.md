# Founder-Facing Copy

Every word the founder can ever read, in one place. Companion to [README.md](README.md), which
explains the interface these strings live in.

The shipped strings live in [capabilities.json](../catalog/capabilities.json)
(`founder_description` and `verify.founder_proof`), and the catalog wins wherever the two differ.
This file is the design draft and the wording reference for new strings. It's kept as one page
because the [language rule](README.md#the-language-rule) is only checkable when all the strings
sit side by side. Some screens below (the confirmation checklist, the failure actions) are design
only; see the [README's status table](README.md#status-whats-built-and-whats-design).

**The rule these all obey:** understandable by someone who has never heard of cloud
infrastructure. No service names, no infra nouns, no protocols, no file paths, no error codes.

---

## Status words

The complete set. Nothing else may appear as a status.

| Shown | Means |
|---|---|
| `setting up…` | In progress. Also covers "started but not yet proven" — see below. |
| `working` | Proven by a real check. Always accompanied by a proof sentence. |
| `not working yet` | The check ran and failed. Honest, not softened. |
| `stopped — needs a person` | Escalated after one retry. |
| `waiting on your answer` | A question is open. |

**There is no status meaning "started but unverified."** Something that has been created but has
not passed its check stays `setting up…`. It never gets to look like success.

---

## Proof sentences

The sentence under each `working` row. **Never show a sentence stronger than the check that
actually ran** — that is exactly the false confidence this whole project exists to prevent.

Two levels, because the two kinds of check prove genuinely different things:

- **Existence** — the thing is there and answering. Cheap, weak. `aws s3 ls` on an empty bucket
  passes whether or not anything can ever be uploaded to it.
- **Round trip** — write something, read it back, clean up. This is what actually proves the
  capability works.

| Capability | After an existence check | After a round-trip check |
|---|---|---|
| user accounts | "checked that the sign-up system is up and answering" | "created a test account, signed in as them, then deleted it" |
| photo / file storage | "checked that the storage is up and answering" | "stored a test file, read it back unchanged, then removed it" |
| saved information | "checked that the information store is up and ready" | "saved a test record, looked it back up, then removed it" |
| background work | "checked that the background worker is up and ready" | "ran it once with test input and it finished successfully" |
| sending email | "checked that the email sender is up and answering" | "sent a test email and confirmed it went out" |
| work queue | "checked that the work queue is up and ready" | "put a test item in, took it back out, then removed it" |
| stored secrets | "checked that the secure storage is up and ready" | "stored a test value securely and read it back correctly" |
| scheduled task | "checked that the schedule is set and active" | — |
| notifications | "checked that the notification sender is up and ready" | — |
| app settings | "checked that the settings store is up and answering" | — |
| backend | "checked that the backend is up and answering" | — |
| search | "checked that search is up and ready" | — |
| multi-step process | — | "ran the whole process once end-to-end and every step finished" |

The five without a round-trip sentence fall back to the weaker one. That is honest, and the
founder can see it is weaker — which is the point.

**What ships today.** Six capabilities run a real functional check and show the right-hand
sentence: user accounts, file storage, saved information, background work, sending email, and the
multi-step process. The other seven, including the work queue and stored secrets, run an
existence check and show the left-hand sentence. The catalog's `verify.founder_proof` is the
authoritative wording.

---

## Screen text

### Opening

```
  What do you need your product to do?

  ▸ _

  for example:
    "I need users to be able to sign up and log in"
    "users should be able to upload a profile photo"
    "when someone uploads a photo, email them a confirmation"
```

### Confirming the plan

```
  Here's what I'll set up for that:

    ☑ a place to store photos
    ☑ something to resize them
    ☑ a way to send email

    [ set these up ]
```

Unchecking something others depend on:

```
    ☒ something to resize them
      this needs somewhere to put the photos first
```

### When the request is outside what's supported

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

### The board

```
  YOUR PRODUCT

  ● photo storage       working
    stored a test file, read it back unchanged
    last checked 12s ago

  ● accounts            working
    created a test account, signed in as them
    last checked 1m ago

  ○ email               not working yet
    nothing arrived when I sent a test
```

### Failure

```
  ○ email                 not working yet
    nothing arrived when I sent a test

    Your photo storage still works — this
    one piece isn't ready.

    [ try again ]
```

After the retry is spent:

```
  ⊘ email                 stopped — needs a person

    I tried twice and it still isn't working.
    I've stopped rather than keep guessing.

    Everything else is still fine.
```

---

## Translation reference

For anyone writing new strings.

| Never write | Write |
|---|---|
| "Provisioned an S3 bucket" | "a place to store photos" |
| "Configured a Cognito user pool" | "a way for people to sign up and log in" |
| "Created a DynamoDB table" | "somewhere to keep your information" |
| "Deployed a Lambda function" | "something that runs when a photo arrives" |
| "SES email delivery configured" | "a way to send email" |
| "Verified the endpoint responds" | "stored a test file and read it back" |
| "AccessDenied: object is protected" | "I can't change these older photos" |
| "Wrote AWS_ENDPOINT_URL to .env" | "connected it to your app" |
| "Container is healthy" | "it's up and answering" |
| "Retrying with exponential backoff" | "trying again" |

Three rules:

1. **Describe what it does for their product, never what it is.** A founder cares that people can
   upload photos, not that object storage exists.
2. **Use the words they used.** If they said "photos," the row says photos — not "files," not
   "objects," not "media assets."
3. **A sentence that needs a follow-up explanation has failed.** There is no tooltip, no
   drill-down, no "learn more." One plain sentence, or it goes back to be rewritten.
