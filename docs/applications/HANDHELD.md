# Handheld: voice, text and location

**Product requirement: voice plus text and location.** There is no released handheld board, source implementation, complete BOM or qualified radio/codec combination. The V2 vehicle board is not itself a complete communicator: microphone, speaker/audio path, display, user controls, portable power and peer software remain to be designed.

## Define the experience before selecting hardware

| User activity | Required behavior | Failure the UI must explain |
|---|---|---|
| Voice conversation | Deliberate push-to-talk ownership, visible transmit/receive state and bounded live-audio delay | Busy peer/channel, expired audio, unavailable link or rejected session |
| Recorded voice, if selected as a supported mode | Bounded recording, transfer progress and playable completed message | Interrupted/failed transfer; no false delivered state |
| Text message | Selected peer, message identity, bounded retry and duplicate suppression | Pending, delivered or failed; delivered does not mean read |
| Share location | Consent/action to share, fix validity/age and units | No fix, stale fix or offline peer |
| Control an RC vehicle | Visible vehicle/profile and explicit arm/disarm with local vehicle failsafe | Incompatible profile, blocked arm request or lost control link |

Live push-to-talk versus recorded voice delivery remains an unresolved operating choice. Evaluate live speech explicitly; a recorded-message experiment must not silently replace the voice-conversation requirement. Use [the platform concept](../../reviews/codex/PLATFORM_CONCEPT.md) as the shared service architecture.

## Prototype parts and connections

Build a two-endpoint test arrangement with candidate radio development boards and suitable antennas, MCU/audio development hardware, microphone/capture and speaker/headset playback, display/controls or a temporary host UI, GNSS input or clearly marked replay data, validated power and timing instruments. Record exact parts and wiring for each candidate; there is no approved shopping list yet.

Keep radio transport behind a documented interface so codec/message experiments do not alter vehicle output control. Do not connect this experiment to propulsion. The vehicle endpoint must validate command session, sequence, integrity and authority separately from text/voice traffic. A sender address and CRC alone do not establish authentication.

## Startup and use after release

1. Start both endpoints and select the intended peer. Show local and peer battery/link state, radio profile and active application.
2. For text, compose/send and display pending until the defined delivery acknowledgement arrives. Display failure when the retry limit expires; retain a clear retry action.
3. For location, request/share only a valid fresh fix. Show its age at the receiver and update the state when the sender loses fix or disconnects.
4. For voice, request a session, wait for admission and use push-to-talk. End talk explicitly; discard audio that misses the live playback deadline instead of playing an ever-growing backlog. The released control must describe whether simultaneous talk is denied or arbitrated.
5. If RC control is also active, show that state continuously. Admit voice/text traffic only within the measured control budget. If that budget cannot be met, the release must enforce its chosen mode restriction or independently validated radio arrangement.

Buttons, menu labels, pairing gestures and shell commands are to be specified by the actual implementation. They are not existing controls on the vehicle viewer.

## Shutdown after release

End voice, settle or visibly cancel queued transfers, and stop location sharing. If controlling a vehicle, complete its explicit disarm and physical shutdown procedure first. Then power off the handheld; a peer must show the resulting offline state and must not resume an old RC session on reconnect.

## Validate voice and RC together

The longest packet already on air blocks a half-duplex channel even if a control queue has priority. Before committing a radio, measure codec output plus protocol/security/module overhead, packet duration, turnaround, retries, end-to-end audio delay and the worst command age.

| Test | Evidence to save |
|---|---|
| Voice alone under increasing loss | Speech samples, codec settings, frame size, loss, latency and intelligibility evaluation |
| Continuous voice + telemetry + RC | Timestamped command reception, maximum command age, output traces and timeout behavior |
| Peer disappears during talk or text | Transfer/session expiry, UI state and no stale playback or control recovery |
| Mode switch / reconnect at nonzero joystick | Vehicle remains disarmed until a fresh permitted arm sequence |
| Weak link and incompatible profile | Useful failure feedback, bounded retries and no hidden control starvation |

Numeric acceptance limits for speech delay/intelligibility, operating range, control age, power and applicable radio profile must be recorded before selecting hardware. This packet claims no range, live-voice performance, license/regional compliance or voice/RC coexistence result.

**Next task:** implement a repeatable two-endpoint audio/airtime experiment and agree the required voice mode and timing limits. Compare measured results against the RC timeout budget before choosing the handheld radio, codec and pin allocation. Store the configuration and results using the [acceptance record](ACCEPTANCE_RECORD.md).
