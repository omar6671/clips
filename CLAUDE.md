# Arabic clipping — working notes for Claude

This repo hosts finished clips (public raw links for Buffer) and the tools used to make them.
Read this whole file before doing anything.

## How to work with the owner
- **Do only what is asked.** Don't start uploads, posting, scheduling or extra work unprompted. Don't give long plans.
- Answer the exact question, briefly. Long reports don't get read; short summaries do.
- Never post anything twice. Never upload/post without being told.
- Use Morocco time when the owner gives times. Buffer times have been written in UTC with Morocco = UTC (the owner's "10 AM" = 10:00Z).

## Getting source videos
- The owner shares Google Drive links ("Anyone with the link"). Download with:
  `curl -sS --fail -o src.mp4 "https://drive.usercontent.google.com/download?id=FILE_ID&export=download&confirm=t"`
  Drive supports byte ranges (`-r`), so for huge files you can fetch only the parts you need.
- "Quota exceeded" = file owned by another account is over its download limit: ask the owner to make a copy in their own Drive and share that.
- YouTube downloads from the cloud are blocked ("confirm you're not a bot"). The owner downloads on their laptop with yt-dlp
  (`--download-sections "*H:MM:SS-H:MM:SS"` for parts) and uploads to Drive.

## Picking moments (most important)
- Only real moments: people talking / reacting / something happening on screen. 15–60 s each.
- **Never** clip promo/intro/sponsor segments, a single person reading an announcement, map/loading screens, dark empty shots, dead air, end-of-stream thank-yous.
- Fewer good clips beats padding with weak ones. Snap starts/ends to sentence boundaries (word timestamps).
- Clips from one source must not overlap.

## Hooks
- Always write Abofalah as **أبو فله** (never ابو فلاح) in hooks, captions and posts.
- Black text on a white rounded box (single solid box — no "stairs" of per-line boxes). `tools/hookimg.py` with `single=True`, size 60.
- **Max 2 lines.** Write the best hook first, then fit it in ≤2 lines. Don't force 1 line. Break lines at natural phrase points: use `|` in the hook text to force the break.
- Khaliji/Saudi dialect, with contextual emojis. Every clip gets a different hook; vary the structure (not all "X ما توقع Y…").
- Style that works (owner's examples): names + reaction/surprise + game, e.g. "كانسل ما توقع شونق لعيب لذي الدرجة في كود مودرن وارفر ٤ 😳🔥", "باور يلعبون اول قيم في MW4 مع افضل لاعب كود كانسل 😂🔥🔥".
- Only name people you are sure about.
- Never on top of a face. Never touching the top of the screen (TikTok UI covers the top ~200 px).
- English words/numbers (GTA 6, MW4) must read in the right order — hookimg.py handles this.
- **Duration rule (updated 2026-11-22 from the top-30 study):** the hook stays for the **whole clip** in every layout, including the split-screen seam (top podcast clips keep the white box on the seam the whole time).

## Captions
- **Only add captions when the owner asks, and only on the clips he names.**
- Saudi/Khaliji dialect (translate English speech into Saudi dialect). Simple white Vazirmatn with thin black outline.
- Timing must match speech like CapCut: appear when the words start, disappear when they stop, nothing during silence.
  Whisper times are often early — use word timestamps (re-transcribe the clip with `vad_filter=False`) and `tools/capsnap.py` to snap to the voice.
- No gaps while someone is talking; correct garbled whisper text by hand, and drop words you can't verify.
- Placement: split-screen → on the seam line (below the hook during the first 4.5 s); single video → near the bottom of the video.

## Voiceover videos (gameplay/trailer + AI voice)
- Voice: ElevenLabs **Abdullah Saadoun** (`t9akNmCDhz230CEXOYmn`), model `eleven_v4`, stability 0.42, similarity 0.74, style 0, no speed change (owner approved — don't change settings unless asked). Key is injected by the proxy (header `xi-api-key: proxy-injected`).
- Topics: anything interesting about the game that can get views. Examples only (not a fixed list): hackers/anti-cheat news, new features, small details most players miss, game info/news, tips. Openers seen in top videos: "90% من اللعيبة…", "انتبه…", "عاجل ورسمياً…", "تخيّل…". Story-style is OK too, but keep it punchy, not a list of facts.
- Learn from the example videos but **NEVER copy their scripts or parts of them** — always write our own wording. Only state facts we can verify (trailers, official info).
- Footage: mix shots from at least 2 different trailers (Drive `Trailers (for voiceover)`), cut every ~2–3 s to match the words, mute trailer audio (voice only), crop out burned-in subtitles. Hook in white box above the video for the whole clip, big white captions synced to the voice.

## Layouts (all 1080×1920, 30 fps, H.264 CRF 18, AAC 192k, loudnorm −14 LUFS, +faststart)
- **Split screen (campaign / facecam streams):** facecam zoomed in on top (crop inside the cam border, no frame visible, sharpen with `cas`, don't overdo it), gameplay below (crop out burned-in subtitles), hook centred on the seam for 4.5 s. Crop must follow whoever is on cam. `render_cam.py`, `render_v6.py`, `render_split.py`.
- **Normal / warm-up:** video zoomed in on black (or square face-tracked crop), hook in the black space above, whole clip. `render_single.py`, `render_v6.py` (version `_b`).
- Warm-up batches are made in **both** versions per moment when asked (`_a` split, `_b` normal).
- Check every render: `tools/qa.py OUTDIR` (decode, A/V length, loudness, faststart) + look at frames. Fix loudness with a volume pass if outside −16.5…−11.5.

## Posting (Buffer API)
- `tools/buffer_post.py CHANNEL_ID tiktok|instagram VIDEO_URL DUE_ISO|now CAPTION_FILE`
  - TikTok channel: `6afac1e7ece6dfde5fe16b6a` — Instagram channel: `6afac0abece6dfde5fe1635f`
  - The Buffer API key is stored in the cloud environment (proxy injects it) — never put it in files.
- Video must be a public URL: commit the mp4 here and use `https://raw.githubusercontent.com/omar6671/clips/main/<path>`.
- Each video goes to TikTok and Instagram at the same time, with a different engaging Khaliji caption each time.
- Channels now: TikTok `6afac1e7ece6dfde5fe16b6a` + X `6b03121f8541f09ecb65a5cc` (Instagram removed). Every video goes to both.
- **Campaign (official) content:** tag `@callofdutyarabic` on TikTok, `@CallofDutyARA` on X, then hashtags with **#ad always first**: TikTok `#ad #كود #mw4 #callofduty #اكسبلور` (+ topic tag e.g. #اوسمز #تي_ام_فيصل #DMZ #وارزون), X `#ad #كود #MW4` (+ topic tag). Always, on every campaign post.
- **Schedule:** 4 posts/day at 13:00, 16:00, 19:00, 22:00 Morocco, alternating days: (campaign, campaign, warm-up, campaign) then (campaign, warm-up, campaign, warm-up).
- **Warm-up content:** NO tags, NO #ad, NO hashtags. Just the caption.
- Space posts ~2+ hours; avoid 00:00–09:00 Morocco. Instagram flagged the account for **unoriginal content** after many near-identical clipped posts — prefer original/transformed content, fewer similar posts per day.

## Repo layout
- Branch `claude/affectionate-hawking-iom3sr` (raw links use this branch path until merged to main).
- `abofalah/` warm-up (horror reaction, facecam box): clip01–14. 10 split (cam top / film bottom), 4 wide (frame on black, hook above).
- `bandareta/` warm-up (Saudi horror-comedy film, no facecam): clip01–20, 4:5 face-tracked crop or wide frame, hook above the whole clip. No captions on warm-up.
- `ep2/` campaign (TM فيصل × فهد سال podcast): split, podcast top / Bashar gameplay bottom, hook 4.5 s, captions. clip01–27 (no 16).
- `ep3/` campaign (MW4 challenge, 4K): 01–03,08,09 facecam-top split; 04,05,10–13 podcast/studio top + EP3 gameplay bottom. Many EP3 moments were already posted earlier — check Buffer history before reusing.
- `ep1/` campaign (أوسمز podcast, 4K): split + Bashar gameplay + captions. Already-posted EP1 topics (skip): grocery street closed, London exam 20/20, mom & America, Joy Award, 8 months no income, university no friends, Saudi clubs goalkeeper offer, "people are مصالح", name meaning, closest YouTuber.
- `tools/`: `render_ep.py` (podcast + gameplay split, shot-aware, captions, `gright` = gameplay right edge), `render_box.py` (fixed facecam box layouts), `render_film.py` (film layouts, pre-roll trim for sources that show black after a seek), `clipcaps.py` (large-v3 word-timed captions per clip; fix text by hand after), `hookimg.py` (colours: bw/wb/by/yb).
- Bottom gameplay for EP1/EP2: also use the Kaydra stream (Drive content folder) — not only Bashar — so clips don't repeat the same footage.
- Bashar gameplay is mostly dark in its campaign part; use bright windows only (brightness map) and vary zoom/crop per clip.
- Whisper model: faster-whisper large-v3 (captions) / large-v3-turbo (full-source scan), int8 CPU; set `HF_HUB_DISABLE_XET=1`.
  Fonts: Vazirmatn (install from npm `vazirmatn` if missing), NotoColorEmoji. Python: faster-whisper, pillow (raqm), opencv-python-headless<5, numpy.
- Buffer: list past posts with GraphQL `posts(input:{organizationId:"6afac0182fbcba384e4540d0", filter:{channelIds:[...], status:[sent]}})`; delete with `deletePost(input:{id})`.

## Posting history (as of 2026-11-20)
- Campaign EP1 (Osmz podcast) and EP3 challenge: many clips posted 2026-11-02…18 (see Buffer history). Old files deleted.
- Old warm-up (Shonq suite vlog): 01, 03, 05 posted. Warm-up batch 03 (GTA 6): clip09_a posted; folder deleted 2026-11-20.
- Scheduled 2026-11-20 (Morocco = UTC): 09:00 abofalah/clip07, 13:00 ep2/clip07, 18:00 bandareta/clip17 — each on TikTok + Instagram.

## Weekly workflow (from 2026-11-23)
- Batch one week at a time: campaign for the whole week (voiceovers prioritised), warm-ups only 3 days ahead (remind owner for fresh warm-up content).
- Files: `weekN/` (vo_*, pod_*, wu_*), plan + captions + queue state in `weekN/post/`. Buffer allows only **10 scheduled posts per channel** → `tools/topup.py weekN/post/plan.json` fills the queue in date order; a daily scheduled task (10:37 Morocco) runs it and checks analytics.
- Week 1 (Nov 23–29): 11 voiceovers + 7 podcast clips (Kaydra part2 gameplay, box hook) + 4 أبو فله GTA 6 warm-ups (Mon–Wed; wide full-frame layout because he switches between cam box and full-screen face).
