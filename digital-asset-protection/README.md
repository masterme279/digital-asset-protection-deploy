# Digital Asset Protection Pipeline

Production-style multimodal piracy detection and ownership verification for:

- Images (CLIP + DINOv2)
- Videos (frame extraction + temporal/summary matching)
- Audio (Chromaprint + Wav2Vec2)
- Watermark verification (DCT + ECDSA)
- Vector search (Milvus)

## 1) Quick Start

### Prerequisites

- Python 3.10+
- Docker Desktop (for Milvus)
- FFmpeg installed and available in PATH

### Environment Setup

From project root:

```powershell
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt
pip install -e .
```

### Start Milvus

```powershell
docker compose up -d
docker compose ps
```

Milvus must be reachable on `localhost:19530`.

## 2) Real Dataset Layout

Use this exact directory structure under `data/raw`:

```text
data/raw/
	image/
		original/
		positive/
		negative/
	video/
		original/
		positive/
		negative/
	audio/
		original/
		positive/
		negative/
```

Definitions:

- `original`: legitimate source assets
- `positive`: stolen/edited/recoded versions of originals
- `negative`: unrelated files

## 3) Single Real Checks

### Image

```powershell
python -m ai_pipeline.scripts.run_pipeline check-image --original data/raw/image/original/img1.jpg --candidate data/raw/image/positive/img1_crop.jpg
```

### Video

```powershell
python -m ai_pipeline.scripts.run_pipeline check-video --original data/raw/video/original/v1.mp4 --candidate data/raw/video/positive/v1_trimmed.mp4
```

### Audio

```powershell
python -m ai_pipeline.scripts.run_pipeline check-audio --original data/raw/audio/original/a1.wav --candidate data/raw/audio/positive/a1_reencoded.mp3 --audio-device cpu
```

## 4) Full Real Evaluation

Run the full multimodal evaluation (all modalities together):

```powershell
python -m ai_pipeline.scripts.run_pipeline evaluate --dataset-root data/raw --modalities image video audio --audio-device cpu --output reports/evaluation_report.json
```

Run only selected modalities:

```powershell
python -m ai_pipeline.scripts.run_pipeline evaluate --dataset-root data/raw --modalities image video
python -m ai_pipeline.scripts.run_pipeline evaluate --dataset-root data/raw --modalities audio --audio-device cpu
```

The command prints per-modality metrics and saves JSON report.

## 5) Score Interpretation

Target for strong real-world readiness:

- Precision >= 0.90
- Recall >= 0.85
- Accuracy >= 0.90

If precision is low:

- Too many negatives are incorrectly flagged.
- Tighten thresholds in modality analyzers.

If recall is low:

- Too many edited copies are missed.
- Relax thresholds or improve dataset diversity.

## 6) Vector DB Verification

Milvus integration tests:

```powershell
python -m pytest ai_pipeline/tests/test_vector_db.py -v
```

Full test suite:

```powershell
python -m pytest ai_pipeline/tests -v
```

## 7) Top-Level Entrypoint

You can also run via:

```powershell
python main.py evaluate --dataset-root data/raw --audio-device cpu
```

Or just run with no args (defaults to evaluation):

```powershell
python main.py
```

## 8) Watermark

Run watermark embed + verify tests:

```powershell
python -m pytest ai_pipeline/tests/test_watermark.py -v
```

## 9) Current Notes

- First run can be slow because model weights are downloaded.
- Use `--audio-device cuda` if GPU is available.
- Keep test data legal and permission-safe.

## 10) Phase 1 Live Ingestion Server

Run the API server:

```powershell
python -m ai_pipeline.scripts.run_phase1_server --host 127.0.0.1 --port 8080 --sample-root data/raw
```

Notes:

- First run can be slow (model weights download).
- Real URLs are downloaded and cached under `data/processed/media_cache/`.
- YouTube video downloads use `yt-dlp` (and may require ffmpeg depending on the format).

Health check:

```powershell
curl http://127.0.0.1:8080/health
```

Ingest mock YouTube posts from local dataset folders:

```powershell
curl -X POST "http://127.0.0.1:8080/ingest/youtube/mock?limit=20"
```

### Real-time ingestion (YouTube / X / Instagram)

Set environment variables (PowerShell examples):

```powershell
# YouTube Data API v3
$env:YOUTUBE_API_KEY = "..."
$env:YOUTUBE_QUERY = "your keywords"          # optional if using channel
$env:YOUTUBE_CHANNEL_ID = "UC..."            # optional if using query

# X (Twitter) API v2
$env:X_BEARER_TOKEN = "..."
$env:X_QUERY = "has:media -is:retweet"       # or your own query

# Instagram Graph API
$env:IG_ACCESS_TOKEN = "..."
$env:IG_USER_ID = "..."

# Reddit (public JSON API)
$env:REDDIT_USER_AGENT = "digital-asset-protection/0.1 (hackathon)"
$env:REDDIT_QUERY = "uefa highlights"          # optional if using subreddit
$env:REDDIT_SUBREDDIT = "soccer"              # optional if using query
```

Trigger one-time fetch + enqueue (dashboard button style):

```powershell
curl -X POST "http://127.0.0.1:8080/ingest/youtube/real?limit=10"
curl -X POST "http://127.0.0.1:8080/ingest/x/real?limit=25"
curl -X POST "http://127.0.0.1:8080/ingest/instagram/real?limit=10"
curl -X POST "http://127.0.0.1:8080/ingest/reddit/real?limit=25"
```

Enable continuous polling ("real-time"):

```powershell
$env:PHASE1_ENABLE_POLLERS = "1"
$env:PHASE1_POLL_INTERVAL_SEC = "30"
python -m ai_pipeline.scripts.run_phase1_server --host 127.0.0.1 --port 8080 --sample-root data/raw
```

List detection cases (dashboard feed):

```powershell
curl "http://127.0.0.1:8080/cases?limit=50"
```

Get one case detail:

```powershell
curl http://127.0.0.1:8080/cases/<case_id>
```

The server currently includes:

- YouTube connector interface and mock ingestion implementation
- Queue-based detection worker
- Case repository for dashboard consumption
- Decision tiers (auto notice, human review, monitor, ignore)

Phase 1.1 persistence:

- Ingestion jobs, detection cases, and audit events are persisted in SQLite at
	`data/processed/phase1_pipeline.db`

Audit feed endpoint:

```powershell
curl "http://127.0.0.1:8080/audit?limit=100"
```

Production migration path:

- Replace polling with official webhooks/streaming where available
- Persist cases/jobs in Postgres
- Move queue to Kafka/RabbitMQ/SQS
