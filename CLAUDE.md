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
- Black text on a white rounded box (single solid box — no "stairs" of per-line boxes). `tools/hookimg.py` with `single=True`, size 60.
- **Max 2 lines.** Write the best hook first, then fit it in ≤2 lines. Don't force 1 line. Break lines at natural phrase points: use `|` in the hook text to force the break.
- Khaliji/Saudi dialect, with contextual emojis. Every clip gets a different hook; vary the structure (not all "X ما توقع Y…").
- Style that works (owner's examples): names + reaction/surprise + game, e.g. "كانسل ما توقع شونق لعيب لذي الدرجة في كود مودرن وارفر ٤ 😳🔥", "باور يلعبون اول قيم في MW4 مع افضل لاعب كود كانسل 😂🔥🔥".
- Only name people you are sure about.
- Never on top of a face. Never touching the top of the screen (TikTok UI covers the top ~200 px).
- English words/numbers (GTA 6, MW4) must read in the right order — hookimg.py handles this.
- **Duration rule:** hook in the middle over video (split-screen seam) → show only the first ~4.5 s. Hook in empty black space above the video → keep it for the whole clip.

## Captions
- **Only add captions when the owner asks, and only on the clips he names.**
- Saudi/Khaliji dialect (translate English speech into Saudi dialect). Simple white Vazirmatn with thin black outline.
- Timing must match speech like CapCut: appear when the words start, disappear when they stop, nothing during silence.
  Whisper times are often early — use word timestamps (re-transcribe the clip with `vad_filter=False`) and `tools/capsnap.py` to snap to the voice.
- No gaps while someone is talking; correct garbled whisper text by hand, and drop words you can't verify.
- Placement: split-screen → on the seam line (below the hook during the first 4.5 s); single video → near the bottom of the video.

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
- **Campaign (official) content:** tag `@callofdutyarabic` on TikTok, `@callofdutyara` on Instagram, and `#ad` on both — always.
- **Warm-up content:** NO tags, NO #ad, NO hashtags. Just the caption.
- Space posts ~2+ hours; avoid 00:00–09:00 Morocco. Instagram flagged the account for **unoriginal content** after many near-identical clipped posts — prefer original/transformed content, fewer similar posts per day.

## Repo layout
- `warmup/` — warm-up batch 03 (GTA 6 stream): `clipNN_a.mp4` (split), `clipNN_b.mp4` (normal), NN = 01–11.
- `tools/` — the scripts above. Whisper model: faster-whisper large-v3 (int8, CPU); set `HF_HUB_DISABLE_XET=1`.
  Fonts: Vazirmatn (Arabic), NotoColorEmoji. Python: faster-whisper, pillow (raqm), opencv-python-headless<5, numpy.

## Posting history (as of 2026-11-20)
- Campaign EP1 (Awesomes podcast, split screen): clips 01–08 posted. Files deleted from GitHub.
- Campaign EP3 challenge (MW4 facecam): clips 21–26 posted; 27–30 cancelled (not posted). Files deleted.
- Old warm-up (Shonq suite vlog): clips 01 (deleted by owner), 03, 05 posted.
- Warm-up batch 03 (GTA 6): `clip09_a` posted 2026-11-19 23:04 UTC. The other 21 are unposted.
