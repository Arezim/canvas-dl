# canvas-dl

A user-friendly CLI tool to download files from UVA Canvas courses, featuring secure token management, interactive course selection, and robust downloading with filtering options.

## Features

- 🔐 **Secure Authentication**: Local token storage with environment variable support
- 📚 **Interactive Course Selection**: Browse and select courses with a user-friendly interface
- 🎯 **Smart Filtering**: Filter files by type, name patterns, and regex
- ⚡ **Concurrent Downloads**: Configurable parallel downloads with rate limiting
- 📊 **Rich Output**: Beautiful terminal interface with progress tracking
- 🛡️ **API Compliance**: Respects Canvas API rate limits and pagination

## Installation

### Prerequisites
- Python 3.9 or higher
- A Canvas access token (see [Getting Your Token](#getting-your-token))

### Install with uv (recommended)

```bash
# Clone the repository
git clone <repository-url>
cd canvas-dl

# Create virtual environment and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

### Alternative installation

```bash
pip install -e .
```

## Quick Start

1. **Get your Canvas access token** (see instructions below)
2. **Configure the token**:
   ```bash
   canvas-dl auth
   ```
3. **List your courses**:
   ```bash
   canvas-dl courses --published
   ```
4. **Download files**:
   ```bash
   canvas-dl download --course-id 45952
   ```

## Getting Your Token

1. Log into your Canvas account at [canvas.uva.nl](https://canvas.uva.nl)
2. Go to **Settings** → **Approved Integrations**
3. Click **New Access Token**
4. Give it a name (e.g., "canvas-dl")
5. Set an expiration date
6. Copy the generated token (you won't see it again!)

## Usage

### Authentication

Configure your Canvas access token:

```bash
canvas-dl auth
```

You can also set environment variables:
```bash
export ACCESS_TOKEN="your-token-here"
export CANVAS_API_URL="https://canvas.uva.nl/api/v1"  # optional
```

### Listing Courses

List all your courses:
```bash
canvas-dl courses
```

Show only published courses:
```bash
canvas-dl courses --published
```

### Downloading Files

#### Basic Download
Download all files from a specific course:
```bash
canvas-dl download --course-id 45952
```

#### Interactive Selection
Let the tool help you choose a course:
```bash
canvas-dl download
```

#### Filtering Options

Filter by file types:
```bash
canvas-dl download --course-id 45952 --only pdf,ipynb,docx
```

Filter by name pattern (glob):
```bash
canvas-dl download --course-id 45952 --name "*lecture*"
```

Filter by regex:
```bash
canvas-dl download --course-id 45952 --regex ".*assignment.*"
```

#### Custom Settings

Set destination directory:
```bash
canvas-dl download --course-id 45952 --dest ~/UVA/Causality
```

Configure concurrent downloads:
```bash
canvas-dl download --course-id 45952 --concurrency 4
```

#### Advanced Examples

Download only PDF lectures to a specific folder:
```bash
canvas-dl download --course-id 45952 --only pdf --name "*lecture*" --dest ~/UVA/Lectures
```

Download with custom API URL:
```bash
canvas-dl download --course-id 45952 --api-url "https://your-canvas-instance.com/api/v1"
```

## Command Reference

### `canvas-dl auth`
Configure your Canvas access token interactively.

**Options:**
- `--api-url`: Canvas API base URL (default: https://canvas.uva.nl/api/v1)

### `canvas-dl courses`
List your Canvas courses in a table format.

**Options:**
- `--published`: Only show published courses
- `--api-url`: Override API URL
- `--token`: Override access token

### `canvas-dl download`
Download files from a Canvas course.

**Options:**
- `--course-id`: Course ID to download (if not provided, interactive selection)
- `--dest`: Destination directory (default: ./downloads)
- `--only`: Filter by file types (comma-separated, e.g., pdf,ipynb)
- `--name`: Filter by name pattern (glob syntax)
- `--regex`: Filter by name pattern (regex)
- `--concurrency`: Number of concurrent downloads
- `--api-url`: Override API URL
- `--token`: Override access token

### `canvas-dl version`
Show the current version.

### `canvas-dl help`
Show detailed help information.

## Configuration

### Environment Variables
- `ACCESS_TOKEN`: Your Canvas access token
- `CANVAS_API_URL`: Canvas API base URL (optional)

### Config File
The tool stores configuration in a local file. The location varies by platform:
- **macOS**: `~/Library/Application Support/canvas-dl/config.toml`
- **Linux**: `~/.config/canvas-dl/config.toml`
- **Windows**: `%APPDATA%\canvas-dl\config.toml`

## File Organization

Downloaded files are organized as follows:
```
downloads/
└── Course Name/
    ├── Module 1/
    │   ├── lecture1.pdf
    │   └── assignment1.ipynb
    └── Module 2/
        ├── lecture2.pdf
        └── slides.pptx
```

## Troubleshooting

### Common Issues

**"Missing access token" error**
- Run `canvas-dl auth` to configure your token
- Or set the `ACCESS_TOKEN` environment variable

**"Error listing courses" error**
- Check your internet connection
- Verify your access token is valid
- Ensure you have access to the Canvas instance

**Download fails**
- Check available disk space
- Verify file permissions in destination directory
- Try reducing concurrency with `--concurrency 1`

### Getting Help

For detailed help:
```bash
canvas-dl help
```

For command-specific help:
```bash
canvas-dl <command> --help
```

## Development

### Setup Development Environment
```bash
git clone <repository-url>
cd canvas-dl
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Running Tests
```bash
pytest
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
