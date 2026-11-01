# Situation Monitor Fetch Scripts

This directory contains standalone fetch scripts for various situation monitoring websites. These scripts are designed to work **without authentication** and **without installation** - they can be copy-pasted and run directly in cloud VMs or free AI chat apps like Gemini or ChatGPT.

## Overview

Each target website has both a **Bash shell script** (`.sh`) and a **Python script** (`.py`) available. The Python scripts generally offer more robust extraction and error handling, while the Bash scripts are more portable and work in environments where Python might not be available.

## Target Websites

| Website | Script (Bash) | Script (Python) | Description |
|---------|--------------|----------------|-------------|
| [WorldMonitor](https://www.worldmonitor.app) | [`fetch_worldmonitor.sh`](fetch_worldmonitor.sh) | [`fetch_worldmonitor.py`](fetch_worldmonitor.py) | Global situation monitoring |
| [IranMonitor](https://www.iranmonitor.org) | [`fetch_iranmonitor.sh`](fetch_iranmonitor.sh) | [`fetch_iranmonitor.py`](fetch_iranmonitor.py) | Iran-focused news and analysis |
| [PressReader](https://www.pressreader.com) | [`fetch_pressreader.sh`](fetch_pressreader.sh) | [`fetch_pressreader.py`](fetch_pressreader.py) | Newspaper and magazine articles |
| [Pizzint.watch](https://www.pizzint.watch) | [`fetch_pizzint.sh`](fetch_pizzint.sh) | [`fetch_pizzint.py`](fetch_pizzint.py) | Intelligence and monitoring platform |
| [Pizzint Polyglobe](https://www.pizzint.watch/polyglobe/app) | [`fetch_polyglobe.sh`](fetch_polyglobe.sh) | [`fetch_polyglobe.py`](fetch_polyglobe.py) | Geospatial visualization |
| [Monitor the Situation](https://monitor-the-situation.com) | [`fetch_monitor_the_situation.sh`](fetch_monitor_the_situation.sh) | [`fetch_monitor_the_situation.py`](fetch_monitor_the_situation.py) | Situation awareness platform |
| [X.com Lists](https://x.com/i/lists) | [`fetch_x_list.sh`](fetch_x_list.sh) | [`fetch_x_list.py`](fetch_x_list.py) | Twitter/X list monitoring |

**Note for X.com Lists:** The generic `fetch_x_list` scripts accept a list ID parameter, so they can fetch any of the three specified X.com lists:
- `1854578015587500532`
- `2009482810529083846`
- `1845220642758803758`

## Common Features

All scripts share these features:

1. **No Authentication Required** - Work without API keys or user accounts
2. **No Installation Required** - Can be copy-pasted and run directly
3. **Portable** - Work in cloud VMs, AI chat apps, and standard terminals
4. **Free Dependencies** - Only use freely available tools (`curl`, `jq`, Python standard library)
5. **Rate Limiting Handling** - Detect and handle rate limits with retry logic
6. **Error Handling** - Gracefully degrade and provide useful error messages
7. **Structured Output** - Clean JSON output with consistent structure
8. **Logging** - Informative logging to help with debugging
9. **Flexible Output** - Can output to file or stdout

## Requirements

### Bash Scripts

- **curl** - For making HTTP requests (pre-installed on most systems)
- **jq** - For JSON formatting (optional, but recommended for pretty output)

Install on Ubuntu/Debian:
```bash
apt update && apt install -y curl jq
```

Install on Alpine:
```bash
apk add curl jq
```

### Python Scripts

- **Python 3.x** - The scripts are compatible with Python 3.6+
- **Optional libraries** - For better extraction (recommended):
  - `requests` - For HTTP requests
  - `beautifulsoup4` - For HTML parsing

Install Python dependencies:
```bash
pip install requests beautifulsoup4
```

**Note:** The scripts are designed to work with just the Python standard library, but the optional libraries provide better extraction capabilities.

## Usage Examples

### Bash Scripts

```bash
# Run a script and output to stdout
./fetch_worldmonitor.sh

# Save output to a file
./fetch_worldmonitor.sh worldmonitor_data.json

# With search query (for PressReader)
./fetch_pressreader.sh "Iran" pressreader_iran.json

# Fetch X.com list
./fetch_x_list.sh 1854578015587500532 x_list_data.json
```

### Python Scripts

```bash
# Run a script and output to stdout
python3 fetch_worldmonitor.py

# Save output to a file
python3 fetch_worldmonitor.py --output worldmonitor_data.json

# With search query
python3 fetch_pressreader.py --query "Iran" --output pressreader_iran.json

# Fetch X.com list with specific method
python3 fetch_x_list.py 1854578015587500532 --method nitter --output x_list.json

# Compact output (less whitespace)
python3 fetch_worldmonitor.py --format compact

# Quiet mode (only show results, no logs)
python3 fetch_worldmonitor.py --quiet
```

## Output Format

All scripts output clean JSON with a consistent structure:

```json
{
  "status": "success",
  "timestamp": "2024-01-01T12:00:00Z",
  "source": "website_url",
  "items_count": 20,
  "data": [...],
  "extracted_at": "2024-01-01T12:00:00Z"
}
```

In case of errors:

```json
{
  "status": "error",
  "message": "Error message",
  "timestamp": "2024-01-01T12:00:00Z",
  "source": "website_url",
  "retry_after": 300
}
```

## Script Details

### fetch_worldmonitor.sh / fetch_worldmonitor.py

Fetches the latest world monitoring data from worldmonitor.app.

**Features:**
- Extracts headlines, dates, and summaries
- Handles pagination
- Multiple extraction strategies

**Example:**
```bash
python3 fetch_worldmonitor.py --limit 30 --output worldmonitor.json
```

### fetch_iranmonitor.sh / fetch_iranmonitor.py

Fetches news articles from iranmonitor.org.

**Features:**
- Extracts article titles, URLs, dates, and summaries
- Handles different article formats
- Search for specific Iran-related content

**Example:**
```bash
python3 fetch_iranmonitor.py --limit 20
```

### fetch_pressreader.sh / fetch_pressreader.py

Fetches articles from PressReader.com.

**Features:**
- Search functionality with query parameter
- Extracts publication names, dates, and snippets
- Handles both search and catalog pages

**Example:**
```bash
python3 fetch_pressreader.py --query "Ukraine" --limit 50 --output news.json
```

### fetch_pizzint.sh / fetch_pizzint.py

Fetches data from pizzint.watch.

**Features:**
- Extracts intelligence updates
- Handles multiple data formats
- Rate limiting detection

**Example:**
```bash
python3 fetch_pizzint.py --output pizzint.json
```

### fetch_polyglobe.sh / fetch_polyglobe.py

Fetches data from the Polyglobe visualization app.

**Features:**
- Extracts geographic data and events
- Finds data endpoints automatically
- Handles embedded JSON in HTML
- Extracts latitude/longitude coordinates

**Example:**
```bash
python3 fetch_polyglobe.py --output polyglobe.json
```

### fetch_monitor_the_situation.sh / fetch_monitor_the_situation.py

Fetches data from monitor-the-situation.com.

**Features:**
- Extracts situation updates
- Handles rate limiting
- Multiple extraction methods

**Example:**
```bash
python3 fetch_monitor_the_situation.py --limit 40
```

### fetch_x_list.sh / fetch_x_list.py

Fetches tweets from X.com (Twitter) lists.

**Features:**
- Multiple fetch methods:
  - `rss` - Try to use RSS feed (default)
  - `nitter` - Use Nitter instances (self-hosted Twitter alternative)
  - `api` - Use Twitter API v2 (requires BEARER_TOKEN environment variable)
- Accepts list ID as parameter
- Rate limiting handling

**Examples:**
```bash
# Using Nitter
python3 fetch_x_list.py 1854578015587500532 --method nitter --output tweets.json

# Using Twitter API v2 (requires BEARER_TOKEN)
export BEARER_TOKEN="your_token_here"
python3 fetch_x_list.py 1854578015587500532 --method api --limit 100

# For the three specified lists:
python3 fetch_x_list.py 1854578015587500532 --output list1.json
python3 fetch_x_list.py 2009482810529083846 --output list2.json
python3 fetch_x_list.py 1845220642758803758 --output list3.json
```

**Note:** For the `api` method, you need a free Bearer token from [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard). Set it as an environment variable:
```bash
export BEARER_TOKEN="your_bearer_token_here"
```

## Running in AI Chat Apps

These scripts can be run directly in free AI chat apps like **Gemini** or **ChatGPT**:

1. **Gemini**:
   - Paste the entire script (e.g., `fetch_worldmonitor.py`)
   - Add your command after it
   - Example: Run the script with `python3 fetch_worldmonitor.py --limit 10`

2. **ChatGPT**:
   - Similar process - paste and run
   - Note: May have execution time limits

3. **Cloud VMs (Google Cloud Shell, AWS CloudShell, etc.)**:
   - Copy the script to the VM
   - Make it executable: `chmod +x fetch_worldmonitor.py`
   - Run it: `python3 fetch_worldmonitor.py`

## Troubleshooting

### Common Issues

1. **Missing dependencies**:
   - For Bash scripts: Install `curl` and `jq`
   - For Python scripts: Ensure Python 3.x is installed

2. **Rate limiting**:
   - The scripts automatically retry after delays
   - If you see rate limit errors, wait and try again later

3. **Website changes**:
   - If a website changes its structure, the extraction might fail
   - The scripts use multiple extraction methods to handle this

4. **Timeout errors**:
   - Increase the timeout by modifying the `TIMEOUT` variable in Bash scripts
   - Or use the `--timeout` parameter in Python scripts (if available)

### Error Output

All scripts provide detailed error messages:

```
[2024-01-01T12:00:00Z] [ERROR] Failed to fetch URL: Connection timeout
[2024-01-01T12:00:00Z] [INFO] Retrying in 5 seconds...
```

## Contributing

If you find issues or want to improve the scripts:

1. Test the script on the target website
2. Check if the website structure has changed
3. Update the extraction patterns accordingly
4. Ensure backward compatibility

## License

These scripts are provided as-is for the situation-monitor skill. They are free to use and modify.

## Version

These scripts were created as part of the situation-monitor skill improvement project.

---

For more information about the situation-monitor skill, see the main [SKILL.md](../SKILL.md) file.
