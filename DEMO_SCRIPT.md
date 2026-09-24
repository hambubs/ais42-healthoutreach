# Demo Script — 5 minutes, roles flexible (swap as you like)

**Driver** = whoever runs the laptop (default: Sahil) · **Narrator** = whoever speaks (split freely)
**Rule of thumb:** the Driver never explains their own clicks — the Narrator does.

| Time | Surface | Action | Narration |
|---|---|---|---|
| 0:00 | Deck slide 2 | Problem slide | "In the provided dataset of 12,000 villages, the average travel to care is 107 minutes. Only 13.8% are within 30 minutes. 2,611 villages are officially underserved." |
| 0:30 | Console :5000 | Show layers (villages risk-colored, district borders) | "This is our command console — every village, colored by health risk, inside its real district." |
| 0:50 | Console | Click ⚡ Run Spatial Optimization (fleet 3) | "Three mobile medical units. DBSCAN finds settlement clusters, greedy MCLP places the units for maximum area coverage — watch the coverage chip: 13.8% to 22.8% of villages under scheduled care. That's 14.75 million people." |
| 1:30 | Phone A | Airplane mode ON → join MMU-GATEWAY → portal pops → tap Maternal | "This village has no cell coverage — the phone is in airplane mode. One tap. Zero installs. AES-128 encrypted before it leaves the form." |
| 2:10 | Tablet | 192.168.4.1/hub → Pull → show ct_sig | "The hub tablet pulls the encrypted queue — you can see the ciphertext signature." |
| 2:30 | Tablet→Laptop | Switch to Wi-Fi → open http://<laptop-ip>:5000/hub → paste → Sync | "The MMU drives back toward coverage… and the alert just appeared live on the console." |
| 2:50 | Console | Click 🚁 UAV card → click the SOS point | "Poor roads, high risk — the rule engine suggests air dispatch: a TechEagle-class Vertiplane X3, 3–5 kg payload, DGCA DigitalSky compliant. Green line means we beat 30 minutes." |
| 3:20 | Dashboard :8501 | Tab 1: before/after + HeiGIT chart | "The impact dashboard — and an independent WorldPop-based study by Heidelberg Institute puts UP at 24.9% within 30 minutes: same story, same order of magnitude." |
| 3:50 | Dashboard | Tab 2: WorldPop BLR pilot | "Our Karnataka pilot view — real population density around the Bengaluru outskirts with the government facility directory overlaid." |
| 4:10 | Dashboard | Tab 3: DHS Live | "This chart is fetched live from the DHS Program API right now — child anemia, 68.1% in the latest NFHS round." |
| 4:30 | Deck slide 11 | SDG close | "SDG 3.8 and 10.2 — care that travels to the people, and geography that stops deciding who survives. Every percentage point is millions of people. Thank you — Team AIS-42." |
| 4:50 | — | Q&A | Punit's prepared answers: synthetic-data honesty · MMU slider scaling · UAV handoff |

## If something breaks (30-second recovery, do not apologize — narrate)

| Failure | Recovery line + action |
|---|---|
| ESP32 won't cooperate | "Let me show you the same flow through a real phone." → phone opens **http://<laptop-ip>:5000/sos** on venue Wi-Fi → taps Maternal → alert pops live on the console |
| Venue Wi-Fi dead | Run everything on the laptop: console + dashboard are local; DHS tab falls back to the local CSV automatically |
| Live API blocked | "The dashboard detects it and falls back to the downloaded DHS data — resilience is part of the design." |
| Total disaster | Play the backup video (deck/demo_backup.mp4) |
