# DHV PDF to Anki

Generate Anki flashcards from DHV (Deutscher Hängegleiterverband) online learning PDF downloads for paragliding training.

## Overview

This tool extracts questions and images from DHV paragliding training PDFs and converts them into Anki flashcard decks. It's designed to help paragliding students study for their DHV license exams using spaced repetition learning.

## Features

- **PDF Question Extraction**: Automatically extracts multiple-choice questions from DHV learning material PDFs
- **Image Processing**: Extracts and processes images referenced in questions
- **AI Enhancement**: Optional integration with Mistral AI to generate additional practice questions (split up questions regarding the gear into separate ones)
- **Anki Deck Generation**: Creates ready-to-import Anki deck files (.apkg format)
- **Web Interface**: Upload PDFs in the browser, generate a deck in a temporary workspace, and download it through a time-limited link
- **Structured Learning**: Organizes questions by sections and subsections from the original material

## Prerequisites

- Python 3.12 or higher
- [Anki](https://apps.ankiweb.net/) desktop application for importing the generated decks

## Just run it (with uv)

```bash
uv tool run --with git+https://github.com/m42e/dhv-pdf-to-anki.git dhv-pdf-to-anki 
```

## Installation

1. Clone this repository:

```bash
git clone git@github.com:m42e/dhv-pdf-to-anki.git
cd dhv_paraglied_to_anki
```

Or if you prefer https:

```bash
git clone https://github.com/m42e/dhv-pdf-to-anki.git
cd dhv_paraglied_to_anki
```

1. Install the package using uv (recommended)

```bash
# Using uv (recommended)
uv sync
```

If you want you could also use pip

```bash
# Or using pip
pip install -e .
```

## Setup

### PDF Files

Place your DHV PDF files in the `pdf/` directory with the following names:

- `Lernstoff.pdf` - The main learning material containing questions (the PDF including the answers)
- `Bilder.pdf` - The image collection referenced by the questions

### Optional: Mistral AI Integration

For AI-enhanced question generation, set your Mistral AI API key:

```bash
export MISTRAL_API_KEY="your-api-key-here"
```

If no API key is provided, the tool will still work but skip the AI enhancement step.

## Usage

### Basic Usage

Run the complete pipeline with default settings:

```bash
dhv-pdf-to-anki
```

This will:

1. Extract images from `pdf/Bilder.pdf` to `images/`
2. Extract questions from `pdf/Lernstoff.pdf`
3. Generate extended questions (if Mistral AI key is available)
4. Create an Anki deck at `output/DHV_Lernmaterial_Fragen.apkg`

### Web Interface

Start the local Flask app:

```bash
dhv-pdf-to-anki-web
```

The web server reads `HOST` and `PORT` from the environment. By default it runs on `127.0.0.1:5000`.
Generated job artifacts are stored under `ARTIFACTS_DIR/<job_id>`. If `ARTIFACTS_DIR` is not set, the app falls back to a temporary system directory.

Then open `http://127.0.0.1:5000` in your browser, upload:

- `Lernstoff.pdf` as the questions PDF
- `Bilder.pdf` as the images PDF

The application will:

1. Copy uploads into an isolated temporary folder
2. Run the same extraction and deck-generation pipeline as the CLI
3. Provide a download link for the generated `.apkg`
4. Remove access to that result after 60 minutes

### Docker

Build the image:

```bash
docker build -t dhv-pdf-to-anki .
```

Run the web app in a container:

```bash
docker run --rm -p 5000:5000 \
  -v "$PWD/artifacts:/artifacts" \
  -e ARTIFACTS_DIR=/artifacts \
  dhv-pdf-to-anki
```

Then open `http://127.0.0.1:5000` in your browser.

If you want AI-enhanced question generation, pass the API key through:

```bash
docker run --rm -p 5000:5000 \
  -v "$PWD/artifacts:/artifacts" \
  -e ARTIFACTS_DIR=/artifacts \
  -e MISTRAL_API_KEY=your-api-key-here \
  dhv-pdf-to-anki
```

Run it with Docker Compose on `127.0.0.1:34209`:

```bash
docker compose up --build
```

Then open `http://127.0.0.1:34209` in your browser.

If you want AI-enhanced question generation with Compose, add the environment variable before starting:

```bash
MISTRAL_API_KEY=your-api-key-here docker compose up --build
```

### Command Line Options

```bash
dhv-pdf-to-anki [OPTIONS]
```

| Option | Description | Default |
| ------ | ----------- | ------- |
| `--pdf-path` | Path to directory containing PDF files | `pdf/` |
| `--anki-deck-name` | Name of the generated Anki deck | `DHV Lernmaterial Fragen` |
| `--output-dir` | Directory to save output files | `output/` |
| `--image-pdf` | Name of the PDF file containing images | `Bilder.pdf` |
| `--questions-pdf` | Name of the PDF file containing questions | `Lernstoff.pdf` |
| `--image-dir` | Directory to save extracted images | `images/` |

The web UI uses its own temporary directories and does not require these CLI paths.

### Example with Custom Options

```bash
dhv-pdf-to-anki \
  --pdf-path ./my-pdfs/ \
  --anki-deck-name "My Custom DHV Deck" \
  --output-dir ./my-output/ \
  --image-pdf MyImages.pdf \
  --questions-pdf MyQuestions.pdf
```

## Directory Structure

After running the tool, your project will have this structure:

```plain
dhv_paraglied_to_anki/
├── pdf/                          # Place your DHV PDF files here
│   ├── Lernstoff.pdf             # Questions PDF
│   └── Bilder.pdf                # Images PDF
├── images/                       # Extracted images (auto-generated)
│   ├── Abbildung_1.png
│   ├── Abbildung_2.png
│   └── ...
├── output/                       # output (auto-generated)
│   ├── DHV_Lernmaterial_Fragen.apkg  # Anki deck file
│   ├── questions.json           # Extracted questions
│   └── extended_questions.json  # AI-generated questions (optional)
└── src/dhv_pdf_to_anki/         # Source code
```

## Importing to Anki

1. Open [Anki](https://apps.ankiweb.net/) on your computer
2. Go to **File** → **Import**
3. Select the generated `.apkg` file from the `output/` directory
4. Click **Import**

Your DHV questions will now be available as a new deck in Anki!

## Question Format

Each flashcard includes:

- **Front**: The question text and any referenced images
- **Back**: Multiple choice answers with the correct answer highlighted
- **Tags**: Section and subsection information for filtering

The answers for a card are shuffled based on the current date, so it will not always be in the same order, to be a bit more of a challenge.

## Troubleshooting

### Common Issues

1. **PDF files not found**: Ensure your PDF files are in the correct directory with the exact filenames
2. **Permission errors**: Make sure the output directory is writable
3. **Images not displaying**: Verify that the image PDF contains the referenced figures

### Debug Information

The tool provides detailed console output showing:

- ✓ Successful operations
- ⚠ Warnings for optional features
- ❌ Errors that need attention

## Links

- [Anki Desktop](https://apps.ankiweb.net/) - Download the Anki application
- [DHV (Deutscher Hängegleiterverband)](https://www.dhv.de/) - Official DHV website
- [Mistral AI](https://mistral.ai/) - AI service for question enhancement

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Author

Matthias Bilger [matthias@bilger.info](matthias@bilger.info)
