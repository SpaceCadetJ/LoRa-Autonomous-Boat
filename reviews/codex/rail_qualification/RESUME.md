# ACT-05 restart record — 2026-10-12

The interrupted ACT-05 screening packet is now complete for its documented analytical scope. The earlier approval-service usage-limit failure prevented one write; normal escalated writes later succeeded. No approval mechanism was bypassed. ACT-04 at cf48ce5 remains the latest native candidate; ACT-05 has zero circuit/copper delta.

Start at [README.md](README.md), [qualification requirements](QUALIFICATION.md), and the newest dated [design handoff](../design_completion/HANDOFF.md). Portable checks: `model.py --check`, `test_model.py`, `build_view.py --check`, `check_packet.py --check`. Browser evidence is in [viewer_check.json](viewer_check.json); no native commands or hardware tests ran for this packet.

Next: screen one adjustable window versus one integrated window/reset alternative, explicitly including assertion and recovery margins, bounded detection conditions, fault retention, supply startup/collapse and edge conditioning. Do not repeat the rejected nominal ±5% TPS3702 assumption. Unimplemented remote-ready, watchdog and ACK permissions stay disabled. Preserve both converters, ACT-01 source populations, R40 at OE, IMU2 and live copper. Inspect Git and ownership before writing; exclude the two unrelated dirty generator/router files from commits.
