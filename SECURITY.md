# Security Policy

## Supported versions

Service Buddy is pre-release (0.1.0). Only the latest `main` is supported. If
you're running something older, update before reporting.

## What this project actually touches

Service Buddy is a local-only development tool. Being honest about the threat
surface is more useful than a long policy, so here's the whole of it:

- It talks to a local [Floci](https://floci.io/) AWS emulator on `http://localhost:4566` using dummy
  `test` / `test` credentials. It does not read, use, or require real AWS
  credentials, and it does not create real cloud resources.
- The only network call it makes to a real external service is an
  unauthenticated fetch of AWS's public Price List API, used for cost estimates.
- Everything else — state, catalog, verification — is local files and local
  processes on your machine.

So the realistic risks are things like a bug that causes the server to write
outside its state directory, shell out unsafely, or mishandle input from a
plain-language request. Those are worth reporting. There is no hosted service,
no user data, and no production deployment to attack.

## Reporting a vulnerability

Report privately through GitHub's private vulnerability reporting: open the
repo's **Security** tab and choose **Report a vulnerability**. You can also email
ahmedkeewan@gmail.com. Please don't open a public issue for anything sensitive.

Include what you found, how to reproduce it, and what you think the impact is.

## What to expect

This is a solo-maintained project, so response is best-effort. You should get an
acknowledgement within a week or so. If a report is valid, the fix lands on
`main` and you'll be credited in the commit unless you'd rather not be.
