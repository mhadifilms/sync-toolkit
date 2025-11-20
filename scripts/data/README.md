# Data Directory

This directory contains template files for various scripts:

## Template Files

- **`spotting_template.csv`** - Template for spotting data (used by `create_shots.py`)
  - Format: Event-based spotting with timecodes (HH:MM:SS:FF)
  - Columns: Project Name, Event Id, Event Name, Event Start Time, Event End Time, etc.
  
- **`input_template.csv`** - Template for S3 input URLs (used by `s3_csv.py`)
  - Format: CSV with VIDEO, AUDIO, ASD columns
  - VIDEO/AUDIO columns contain S3 URIs (s3://bucket/path) or HTTP URLs
  - ASD column: Yes/No for Active Speaker Detection
  
- **`cuts_template.txt`** - Template for timecode cuts (used by `chunk.sh`)
  - Format: Tab-separated values: name<TAB>start_time<TAB>end_time
  - Times can be: HH:MM:SS.mmm or HH:MM:SS:FF (timecode)
  - Lines starting with # are comments

- **`urls_template.txt`** - Template for S3 URL list (used by `s3-download` in list mode)
  - Format: number<TAB>s3://bucket/path/to/file.mov
  - Used for downloading files from a numbered list

## Usage

Copy the template files and customize them for your project:

```bash
cp spotting_template.csv my_project_spotting.csv
cp input_template.csv my_project_input.csv
cp cuts_template.txt my_project_cuts.txt
cp urls_template.txt my_project_urls.txt
```

Then edit the files with your actual data.
