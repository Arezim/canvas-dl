# canvas-dl

A user-friendly CLI to download files from UVA Canvas courses, with token management, course selection, robust downloading, and automatic PDF merging.

## Install

```bash
pipx install .
# or
pip install .
```

## Configure token

```bash
canvas-dl auth
```

Follow the prompt to save your Canvas access token locally. You can also set `ACCESS_TOKEN` in your environment or `.env`.

## Examples

- List courses (published only):

```bash
canvas-dl courses --published
```

- Download all files for a course and merge PDFs (default):

```bash
canvas-dl download --course-id 45952
```

- Interactive picker:

```bash
canvas-dl download
```

- Filter by file types and name pattern:

```bash
canvas-dl download --course-id 45952 --only pdf,ipynb --name "*lecture*" --no-merge
```

- Set destination and concurrency:

```bash
canvas-dl download --course-id 45952 --dest ~/UVA/Causality --concurrency 4
```

## Notes

- Default API base: `https://canvas.uva.nl/api/v1` (override with `--api-url`).
- Token is never printed in logs and is masked in errors.
- Respects Canvas rate limits and uses Link-header pagination.
