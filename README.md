# Study Brainrot Generator

Solo GitHub Actions pipeline: give it a study topic, get back captioned vertical MP4s as build artifacts.

## Setup
1. Repo secrets: `GEMINI_API_KEY` (required), `DEEPSEEK_API_KEY` (fallback, optional but recommended).
2. Drop a few royalty-free vertical loop clips (`.mp4`/`.mov`) into `assets/` (e.g. from Pixabay/Pexels).
   Clips sharing a prefix form one continuous series (`part_00.mp4` … `part_18.mp4`); a bare name
   (`1.mp4`) is a standalone series of one.
3. Actions tab → "Generate Study Video" → Run workflow → enter a topic.
4. Download the MP4s from the run's artifacts.

## Workflow inputs
- `topic` — what to teach.
- `background_group` — which clip series to use, by filename prefix (`part`, `partty`, `1`, …).
  Only that series is fetched from the repo, so a run doesn't download every clip. Alphanumeric,
  plus `_` and `-`.
- `manual_script` — paste script JSON to skip research and the LLM entirely. It is validated
  against the same schema a generated script goes through.

## Repo variables (optional)
`GEMINI_MODEL`, `TTS_VOICE`, `TTS_RATE`, `MAX_VIDEO_SECONDS`.

Only the classic neural voices emit word-boundary metadata; picking a conversational voice
(Andrew, Ava, Emma, Brian) falls back to estimated caption timings.

## Pipeline
`research.py` (Wikipedia) → `script_gen.py` (Gemini, falls back to DeepSeek on rate-limit) →
`voice_gen.py` (Edge-TTS + word timings) → `assemble.py` (FFmpeg karaoke captions + concat).

Chunks are packed into videos of at most `MAX_VIDEO_SECONDS` (default 55) without ever splitting a
chunk, so the output is `build/output_01.mp4`, `build/output_02.mp4`, … — one short-form video each.
