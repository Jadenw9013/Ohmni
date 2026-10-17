# Ohmni PCB Guide

![tag:innovationlab](https://img.shields.io/badge/innovationlab-3D8BD3)
![tag:hackathon](https://img.shields.io/badge/hackathon-5F43F1)

Turn a supported hardware idea into reviewed PCB design files through ASI:One.

- Handle: `@ohmni-pcb-guide`
- Address: `agent1qvzucpk72r48d4gys9npx2an8jjj5mqpzwfjz4yt6a7mnqyag5gzqm5dc32`
- [Public code and setup](https://github.com/Jadenw9013/Ohmni)
- [Run and test instructions](https://github.com/Jadenw9013/Ohmni/blob/main/docs/hackathon/FETCH_AGENT_SETUP.md)

## Try it in ASI

Ask: “I want a USB-powered board to measure the temperature and humidity in my room.”
Review the proposal, answer necessary questions, and send its exact `CONFIRM` code.
The agent generates the design, reports actual checks, and returns a downloadable
ZIP in the conversation. `STATUS` checks progress; `FINDINGS` reads results;
`FILES` refreshes the download link. Ask follow-up questions or request a supported
change, then review and confirm the new plan. No custom frontend is required.

`OPEN` optionally connects the project to Ohmni's saved-project and 3D workspace.
`OPTIONS` lists capabilities. `NEW` followed by requirements starts a separate
plan. `RETRY` explicitly retries a failed confirmed build.

## What executes

Agent Chat Protocol connects ASI to a Python uAgents service. The service uses
Ohmni's planner and deterministic schematic, placement, routing, KiCad checks and
release pipeline. Planning/explanations use Anthropic; models cannot author
engineering passes. Supported families cover USB-powered ESP32 sensor,
button/light and SPI-memory boards. BME280 measures temperature/humidity/pressure,
not smell or air quality. Unsupported goals require an explicit alternative.

## Requirements and limitations

Self-hosting requires Python 3.13, the pinned Fetch extra, KiCad 10.0.5 and its
libraries, native tools described in the setup guide, a private planner API key,
stable private agent seed, HTTPS endpoint and persistent storage. Hosted testing
uses this agent through ASI and is subject to availability and request quotas.

Files require human engineering/manufacturing review. No firmware, assembly,
physical testing, safety qualification, RF/EMC guarantee or verified total cost is
provided. Unknowns and violated requirements remain visible. Download links grant
access to their holders for one hour; optional workspace links grant project
editing access and expire after 30 minutes. Keep links private while valid.
