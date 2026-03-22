from __future__ import annotations

import json
import os
import tempfile
from threading import Thread
from datetime import datetime, timedelta, UTC
from pathlib import Path
from secrets import token_urlsafe

from flask import Flask, abort, jsonify, render_template_string, request, send_file, url_for
from werkzeug.datastructures import FileStorage

from dhv_pdf_to_anki.__main__ import PipelineConfig, run_pipeline


EXPIRY_MINUTES = 60
APP_TITLE = "DHV PDF to Anki"
BASE_ARTIFACTS_DIR = Path(os.getenv("ARTIFACTS_DIR", str(Path(tempfile.gettempdir()) / "dhv-pdf-to-anki-web")))
STATUS_FILENAME = "status.json"

INDEX_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{{ title }}</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f5efe6;
      --card: #fffaf4;
      --ink: #1f2933;
      --accent: #0e7490;
      --accent-strong: #155e75;
      --muted: #52606d;
      --border: #d9cfc1;
      --error-bg: #fdecec;
      --error-fg: #8a1c1c;
      --success-bg: #edfdf4;
      --success-fg: #166534;
    }

    * { box-sizing: border-box; }

    body {
      margin: 0;
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", serif;
      background:
        radial-gradient(circle at top right, rgba(14, 116, 144, 0.14), transparent 28%),
        linear-gradient(180deg, #f8f3eb 0%, var(--bg) 100%);
      color: var(--ink);
      min-height: 100vh;
    }

    main {
      max-width: 820px;
      margin: 0 auto;
      padding: 48px 20px 64px;
    }

    .panel {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      box-shadow: 0 18px 45px rgba(31, 41, 51, 0.08);
      overflow: hidden;
    }

    .hero {
      padding: 32px 32px 20px;
      border-bottom: 1px solid rgba(217, 207, 193, 0.75);
    }

    h1 {
      margin: 0 0 10px;
      font-size: clamp(2rem, 5vw, 3.2rem);
      line-height: 0.98;
      letter-spacing: -0.04em;
    }

    p {
      margin: 0;
      color: var(--muted);
      font-size: 1.05rem;
      line-height: 1.6;
    }

    form {
      display: grid;
      gap: 18px;
      padding: 28px 32px 32px;
    }

    .field {
      display: grid;
      gap: 8px;
    }

    label {
      font-weight: 700;
      font-size: 0.97rem;
    }

    input, select, button {
      font: inherit;
    }

    input[type="text"], select, input[type="file"] {
      width: 100%;
      padding: 13px 14px;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: #fff;
    }

    .checkbox {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 0.97rem;
    }

    .checkbox input {
      width: 18px;
      height: 18px;
    }

    button {
      border: 0;
      border-radius: 999px;
      padding: 14px 22px;
      background: linear-gradient(135deg, var(--accent) 0%, var(--accent-strong) 100%);
      color: #fff;
      font-weight: 700;
      cursor: pointer;
      justify-self: start;
      transition: opacity 0.2s ease, transform 0.2s ease;
    }

    button:hover:not(:disabled) {
      transform: translateY(-1px);
    }

    button:disabled {
      opacity: 0.6;
      cursor: wait;
    }

    .notice {
      margin: 20px 32px 0;
      padding: 14px 16px;
      border-radius: 12px;
      font-size: 0.97rem;
    }

    .notice.error {
      background: var(--error-bg);
      color: var(--error-fg);
    }

    .notice.success {
      background: var(--success-bg);
      color: var(--success-fg);
    }

    .result {
      margin: 20px 32px 32px;
      padding: 18px;
      border-radius: 14px;
      border: 1px solid rgba(22, 101, 52, 0.18);
      background: rgba(237, 253, 244, 0.8);
    }

    .result a {
      color: var(--accent-strong);
      font-weight: 700;
    }

    .progress {
      margin: 0 32px 24px;
      padding: 18px;
      border-radius: 14px;
      border: 1px solid rgba(14, 116, 144, 0.18);
      background: rgba(14, 116, 144, 0.06);
      display: none;
    }

    .progress.visible {
      display: block;
    }

    .progress-head {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      margin-bottom: 10px;
      font-weight: 700;
      font-size: 0.97rem;
    }

    .progress-track {
      width: 100%;
      height: 12px;
      border-radius: 999px;
      background: rgba(31, 41, 51, 0.1);
      overflow: hidden;
    }

    .progress-bar {
      width: 0;
      height: 100%;
      border-radius: 999px;
      background: linear-gradient(90deg, #0e7490 0%, #1d9ab5 100%);
      transition: width 0.35s ease;
    }

    .progress-message {
      margin-top: 10px;
      color: var(--muted);
      font-size: 0.95rem;
    }

    .hint {
      font-size: 0.93rem;
      color: var(--muted);
    }

    @media (max-width: 720px) {
      .hero, form { padding-left: 20px; padding-right: 20px; }
      .notice, .result { margin-left: 20px; margin-right: 20px; }
    }
  </style>
</head>
<body>
  <main>
    <section class="panel">
      <div class="hero">
        <h1>{{ title }}</h1>
        <p>Upload the two DHV PDFs, generate the deck in a temporary workspace, and download the resulting .apkg file. Download links expire after {{ expiry_minutes }} minutes.</p>
      </div>

      {% if error %}
      <div class="notice error">{{ error }}</div>
      {% endif %}

      {% if status %}
      <div class="notice success">{{ status }}</div>
      {% endif %}

      {% if download_url %}
      <div class="result">
        <div><strong>Your deck is ready.</strong></div>
        <div><a href="{{ download_url }}">Download {{ filename }}</a></div>
        <div class="hint">Available until {{ expires_at }} UTC.</div>
      </div>
      {% endif %}

      <div id="progress" class="progress" aria-live="polite">
        <div class="progress-head">
          <span id="progress-label">Preparing upload</span>
          <span id="progress-value">0%</span>
        </div>
        <div class="progress-track">
          <div id="progress-bar" class="progress-bar"></div>
        </div>
        <div id="progress-message" class="progress-message">The job has not started yet.</div>
      </div>

      <form id="generate-form" method="post" action="{{ url_for('generate') }}" enctype="multipart/form-data">
        <div class="field">
          <label for="questions_pdf">Questions PDF</label>
          <input id="questions_pdf" name="questions_pdf" type="file" accept="application/pdf,.pdf" required>
          <div class="hint">Expected content: Lernstoff PDF.</div>
        </div>

        <div class="field">
          <label for="images_pdf">Images PDF</label>
          <input id="images_pdf" name="images_pdf" type="file" accept="application/pdf,.pdf" required>
          <div class="hint">Expected content: Bilder PDF.</div>
        </div>

        <div class="field">
          <label for="deck_name">Deck name</label>
          <input id="deck_name" name="deck_name" type="text" value="{{ deck_name }}" maxlength="120">
        </div>

        <div class="field">
          <label for="language">Card language</label>
          <select id="language" name="language">
            <option value="de" {% if language == 'de' %}selected{% endif %}>Deutsch</option>
            <option value="en" {% if language == 'en' %}selected{% endif %}>English</option>
          </select>
        </div>

        <label class="checkbox" for="save_question_images">
          <input id="save_question_images" name="save_question_images" type="checkbox" value="1" {% if save_question_images %}checked{% endif %}>
          Include cropped question images in the deck
        </label>

        <button id="generate-button" type="submit">Generate Anki Deck</button>
      </form>
    </section>
  </main>
  <script>
    const form = document.getElementById("generate-form");
    const button = document.getElementById("generate-button");
    const progressBox = document.getElementById("progress");
    const progressBar = document.getElementById("progress-bar");
    const progressValue = document.getElementById("progress-value");
    const progressLabel = document.getElementById("progress-label");
    const progressMessage = document.getElementById("progress-message");

    let pollTimer = null;

    function setProgress(progress, message) {
      const safeProgress = Math.max(0, Math.min(100, Number(progress) || 0));
      progressBox.classList.add("visible");
      progressBar.style.width = safeProgress + "%";
      progressValue.textContent = safeProgress + "%";
      progressLabel.textContent = safeProgress >= 100 ? "Completed" : "Generating deck";
      progressMessage.textContent = message || "Working...";
    }

    function setButtonState(disabled, label) {
      button.disabled = disabled;
      button.textContent = label;
    }

    function stopPolling() {
      if (pollTimer !== null) {
        clearTimeout(pollTimer);
        pollTimer = null;
      }
    }

    async function pollStatus(jobId) {
      try {
        const response = await fetch(`/status/${jobId}`, { headers: { "Accept": "application/json" } });
        if (!response.ok) {
          throw new Error("Status request failed");
        }

        const payload = await response.json();
        setProgress(payload.progress, payload.message);

        if (payload.state === "completed") {
          stopPolling();
          setButtonState(false, "Generate Anki Deck");
          window.location.href = `/?job=${encodeURIComponent(jobId)}`;
          return;
        }

        if (payload.state === "failed") {
          stopPolling();
          setButtonState(false, "Generate Anki Deck");
          progressLabel.textContent = "Failed";
          progressMessage.textContent = payload.error || payload.message || "Generation failed.";
          return;
        }

        pollTimer = window.setTimeout(() => pollStatus(jobId), 1200);
      } catch (error) {
        stopPolling();
        setButtonState(false, "Generate Anki Deck");
        progressLabel.textContent = "Failed";
        progressMessage.textContent = "Could not fetch progress updates.";
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      stopPolling();
      setButtonState(true, "Generating...");
      setProgress(5, "Uploading PDFs and creating temporary workspace");

      const formData = new FormData(form);

      try {
        const response = await fetch(form.action, {
          method: "POST",
          body: formData,
          headers: { "Accept": "application/json" },
        });

        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.error || "Generation request failed");
        }

        setProgress(payload.progress, payload.message);
        pollStatus(payload.job_id);
      } catch (error) {
        setButtonState(false, "Generate Anki Deck");
        progressLabel.textContent = "Failed";
        progressMessage.textContent = error.message || "Generation request failed.";
      }
    });
  </script>
</body>
</html>
"""


def create_app() -> Flask:
  app = Flask(__name__)
  BASE_ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

  @app.get("/")
  def index():
    job_id = request.args.get("job", "")
    if job_id:
      state = read_accessible_job_status(BASE_ARTIFACTS_DIR / job_id)
      if state is not None and state.get("state") == "completed":
        return render_index(
          status="Deck generated successfully.",
          download_url=url_for("download", job_id=job_id),
          filename=state_value(state, "filename"),
          expires_at=state_value(state, "expires_at"),
        )
      if state is not None and state.get("state") == "failed":
        return render_index(error=state_value(state, "error") or "Generation failed.")
    return render_index()

  @app.post("/generate")
  def generate():
    questions_pdf = request.files.get("questions_pdf")
    images_pdf = request.files.get("images_pdf")
    deck_name = (request.form.get("deck_name") or "DHV Lernmaterial Fragen").strip() or "DHV Lernmaterial Fragen"
    language = request.form.get("language", "de")
    save_question_images = request.form.get("save_question_images") == "1"

    error = validate_uploads(questions_pdf, images_pdf, language)
    if error:
      return jsonify({"error": error}), 400

    assert questions_pdf is not None
    assert images_pdf is not None

    job_id = token_urlsafe(24)
    job_dir = BASE_ARTIFACTS_DIR / job_id
    pdf_dir = job_dir / "pdf"
    output_dir = job_dir / "output"
    image_dir = job_dir / "images"

    pdf_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)

    write_job_status(
      job_dir,
      {
        "state": "running",
        "progress": 10,
        "message": "Uploading PDFs and creating temporary workspace",
        "filename": None,
        "error": None,
        "expires_at": job_expiry(job_dir).strftime("%Y-%m-%d %H:%M:%S"),
      },
    )

    save_upload(questions_pdf, pdf_dir / "Lernstoff.pdf")
    save_upload(images_pdf, pdf_dir / "Bilder.pdf")

    config = PipelineConfig(
      pdf_path=pdf_dir,
      anki_deck_name=deck_name,
      output_dir=output_dir,
      image_pdf="Bilder.pdf",
      questions_pdf="Lernstoff.pdf",
      image_dir=image_dir,
      language=language,
      save_question_images=save_question_images,
    )
    Thread(target=run_generation_job, args=(job_id, config), daemon=True).start()

    return jsonify(
      {
        "job_id": job_id,
        "progress": 10,
        "message": "Upload complete. Starting generation.",
      }
    )

  @app.get("/status/<job_id>")
  def status(job_id: str):
    if not job_id or "/" in job_id:
      abort(404)

    state = read_accessible_job_status(BASE_ARTIFACTS_DIR / job_id)
    if state is None:
      abort(404)

    response = dict(state)
    if state.get("state") == "completed":
      response["download_url"] = url_for("download", job_id=job_id)
    return jsonify(response)

  @app.get("/download/<job_id>")
  def download(job_id: str):
    if not job_id or "/" in job_id:
      abort(404)

    job_dir = BASE_ARTIFACTS_DIR / job_id
    if not job_dir.exists() or is_expired(job_dir):
      abort(404, description="This download link has expired.")

    output_dir = job_dir / "output"
    matches = sorted(output_dir.glob("*.apkg"))
    if not matches:
      abort(404)

    return send_file(matches[0], as_attachment=True, download_name=matches[0].name, max_age=0)

  return app


def render_index(
    *,
    error: str | None = None,
    status: str | None = None,
    download_url: str | None = None,
    filename: str | None = None,
    expires_at: str | None = None,
    deck_name: str = "DHV Lernmaterial Fragen",
    language: str = "de",
    save_question_images: bool = True,
):
    return render_template_string(
        INDEX_TEMPLATE,
        title=APP_TITLE,
        expiry_minutes=EXPIRY_MINUTES,
        error=error,
        status=status,
        download_url=download_url,
        filename=filename,
        expires_at=expires_at,
        deck_name=deck_name,
        language=language,
        save_question_images=save_question_images,
    )


def validate_uploads(
    questions_pdf: FileStorage | None,
    images_pdf: FileStorage | None,
    language: str,
) -> str | None:
    if not questions_pdf or not questions_pdf.filename:
        return "Please upload the questions PDF."
    if not images_pdf or not images_pdf.filename:
        return "Please upload the images PDF."
    if not questions_pdf.filename.lower().endswith(".pdf"):
        return "The questions file must be a PDF."
    if not images_pdf.filename.lower().endswith(".pdf"):
        return "The images file must be a PDF."
    if language not in {"de", "en"}:
        return "Unsupported language selection."
    return None


def save_upload(upload: FileStorage, destination: Path) -> None:
    upload.save(destination)


def status_file(job_dir: Path) -> Path:
    return job_dir / STATUS_FILENAME


def write_job_status(job_dir: Path, payload: dict[str, object]) -> None:
    status_path = status_file(job_dir)
    status_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_job_status(job_dir: Path) -> dict[str, object] | None:
    status_path = status_file(job_dir)
    if not status_path.exists():
        return None
    return json.loads(status_path.read_text(encoding="utf-8"))


def read_accessible_job_status(job_dir: Path) -> dict[str, object] | None:
  if not job_dir.exists() or is_expired(job_dir):
    return None
  return read_job_status(job_dir)


def state_value(state: dict[str, object], key: str) -> str | None:
    value = state.get(key)
    return value if isinstance(value, str) else None


def run_generation_job(job_id: str, config: PipelineConfig) -> None:
    job_dir = BASE_ARTIFACTS_DIR / job_id

    def report(progress: int, message: str) -> None:
        current_state = read_job_status(job_dir) or {}
        write_job_status(
            job_dir,
            {
                **current_state,
                "state": "running",
                "progress": progress,
                "message": message,
                "error": None,
            },
        )

    try:
        result = run_pipeline(config, progress_callback=report)
        write_job_status(
            job_dir,
            {
                "state": "completed",
                "progress": 100,
                "message": "Deck generated successfully",
                "filename": result.anki_file.name,
                "error": None,
                "expires_at": job_expiry(job_dir).strftime("%Y-%m-%d %H:%M:%S"),
            },
        )
    except Exception as exc:
        write_job_status(
            job_dir,
            {
                "state": "failed",
                "progress": 100,
                "message": "Generation failed",
                "filename": None,
                "error": str(exc),
                "expires_at": job_expiry(job_dir).strftime("%Y-%m-%d %H:%M:%S"),
            },
        )


def job_expiry(job_dir: Path) -> datetime:
    created_at = datetime.fromtimestamp(job_dir.stat().st_mtime, tz=UTC)
    return created_at + timedelta(minutes=EXPIRY_MINUTES)


def is_expired(job_dir: Path) -> bool:
    return datetime.now(UTC) > job_expiry(job_dir)


def main() -> None:
    app = create_app()
    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "5000"))
    app.run(host=host, port=port, debug=False)


app = create_app()