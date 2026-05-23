"""
Migration Script: Obsidian YAML Frontmatter → talent_pool.csv

Reads all 32 candidate .md files from the Obsidian vault,
parses YAML frontmatter, flattens data, writes to CSV.

Run once: python migrate_obsidian_to_csv.py
"""
import os
import csv
import yaml
import re
from pathlib import Path
from datetime import datetime

CANDIDATES_DIR = Path(__file__).parent / "obsidian_db" / "OBSIDIAN-DATA-POOL" / "candidates"
OUTPUT_DIR = Path(__file__).parent / "data"
OUTPUT_FILE = OUTPUT_DIR / "talent_pool.csv"

CSV_COLUMNS = [
    "name",
    "seniority",
    "years_of_experience",
    "current_role",
    "previous_jobs",
    "degrees",
    "location",
    "languages",
    "technologies",
    "project_summary",
    "linkedin_url",
    "github_url",
    "email",
    "status",
    "outreach_status",
    "outreach_date",
    "last_updated_at",
]


def parse_yaml_frontmatter(md_path: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    text = md_path.read_text(encoding="utf-8-sig", errors="replace")
    
    # Match YAML between --- delimiters
    match = re.search(r"^---\s*\n(.*?)\n---", text, re.DOTALL | re.MULTILINE)
    if not match:
        return {}
    
    yaml_text = match.group(1)
    try:
        data = yaml.safe_load(yaml_text)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError as e:
        print(f"  YAML error in {md_path.name}: {e}")
        return {}


def extract_body_sections(md_path: Path) -> dict:
    """Extract key sections from the markdown body (below frontmatter)."""
    text = md_path.read_text(encoding="utf-8-sig", errors="replace")
    
    # Get content after frontmatter
    parts = text.split("---", 2)
    body = parts[2] if len(parts) > 2 else ""
    
    sections = {}
    
    # Extract previous jobs from Experiences tables
    exp_match = re.search(r"## (?:Experiences|Top repos).*?\n((?:\|.*\n)+)", body)
    if exp_match:
        sections["experiences_table"] = exp_match.group(1).strip()
    
    # Extract project summaries
    proj_match = re.search(r"## Projects.*?\n((?:\|.*\n)+)", body)
    if proj_match:
        sections["projects_table"] = proj_match.group(1).strip()
    
    return sections


def flatten_technologies(tech_list) -> str:
    """Flatten technologies list to comma-separated string."""
    if not tech_list:
        return ""
    
    if isinstance(tech_list, str):
        return tech_list
    
    techs = []
    for item in tech_list:
        if isinstance(item, dict):
            tech_name = item.get("tech", "")
            if tech_name:
                techs.append(str(tech_name))
        elif isinstance(item, str):
            techs.append(item)
    
    return ", ".join(sorted(set(techs)))


def flatten_degrees(degrees_list) -> str:
    """Flatten degrees list to readable string."""
    if not degrees_list:
        return ""
    
    parts = []
    for deg in degrees_list:
        if isinstance(deg, dict):
            level = deg.get("level", "")
            field = deg.get("field", "")
            uni = deg.get("university", "")
            if level and level.lower() in ("highschool", "certification"):
                continue  # Skip non-degree entries for brevity
            part = f"{level}: {field}" if field else str(level)
            if uni:
                part += f" @ {uni}"
            parts.append(part)
        elif isinstance(deg, str):
            parts.append(deg)
    
    return "; ".join(parts) if parts else ""


def flatten_languages(lang_list) -> str:
    """Flatten languages list to readable string."""
    if not lang_list:
        return ""
    
    parts = []
    for lang in lang_list:
        if isinstance(lang, dict):
            code = lang.get("lang", "")
            level = lang.get("level", "")
            parts.append(f"{code} ({level})" if level else str(code))
        elif isinstance(lang, str):
            parts.append(lang)
    
    return ", ".join(parts) if parts else ""


def flatten_projects(yaml_data: dict, body_sections: dict) -> str:
    """Create project summary from YAML projects or GitHub repos."""
    summaries = []
    
    # From YAML projects
    projects = yaml_data.get("projects", [])
    if projects:
        for proj in projects:
            if isinstance(proj, dict):
                name = proj.get("name", "")
                desc = proj.get("description", "")
                summary = name
                if desc:
                    # Truncate long descriptions
                    summary += f" — {desc[:100]}"
                summaries.append(summary)
    
    # From GitHub signals
    github = yaml_data.get("github_signals", {})
    if isinstance(github, dict):
        notable = github.get("notable_projects", [])
        for proj in notable:
            if isinstance(proj, dict):
                name = proj.get("name", "")
                stars = proj.get("stars", 0)
                desc = proj.get("desc", "")
                summary = f"{name} ({stars}★)"
                if desc:
                    summary += f" — {desc[:80]}"
                summaries.append(summary)
        
        # Bio as fallback summary
        if not summaries and github.get("bio"):
            summaries.append(github["bio"])
    
    # From technologies_summary (GitHub-scraped profiles)
    tech_summary = yaml_data.get("technologies_summary", "")
    if tech_summary and not summaries:
        summaries.append(f"Tech: {tech_summary}")
    
    return " | ".join(summaries) if summaries else ""


def extract_previous_jobs(yaml_data: dict) -> str:
    """Extract previous jobs from YAML data."""
    jobs = []
    
    # Current company
    company = yaml_data.get("current_company")
    role = yaml_data.get("current_role_title")
    if company and role:
        jobs.append(f"{role} @ {company} (current)")
    elif company:
        jobs.append(f"{company} (current)")
    
    # Last role
    last_company = yaml_data.get("last_company")
    last_role = yaml_data.get("last_role_title")
    if last_company and last_role:
        jobs.append(f"{last_role} @ {last_company}")
    elif last_company:
        jobs.append(str(last_company))
    
    return "; ".join(jobs) if jobs else ""


def process_candidate(candidate_dir: Path) -> dict:
    """Process a single candidate directory into a CSV row."""
    md_files = list(candidate_dir.glob("*.md"))
    if not md_files:
        return None
    
    md_file = md_files[0]
    yaml_data = parse_yaml_frontmatter(md_file)
    body_sections = extract_body_sections(md_file)
    
    if not yaml_data:
        print(f"  Skipping {candidate_dir.name}: no YAML frontmatter")
        return None
    
    name = yaml_data.get("name", yaml_data.get("full_name", ""))
    if not name:
        print(f"  Skipping {candidate_dir.name}: no name found")
        return None
    
    # Extract years of experience
    years_exp = yaml_data.get("years_experience", yaml_data.get("years_on_github", ""))
    
    # Build the row
    row = {
        "name": name,
        "seniority": yaml_data.get("seniority", ""),
        "years_of_experience": str(years_exp) if years_exp else "",
        "current_role": yaml_data.get("current_role_title", ""),
        "previous_jobs": extract_previous_jobs(yaml_data),
        "degrees": flatten_degrees(yaml_data.get("degrees", [])),
        "location": yaml_data.get("location_city", yaml_data.get("location_raw", "")),
        "languages": flatten_languages(yaml_data.get("languages", [])),
        "technologies": flatten_technologies(yaml_data.get("technologies", [])),
        "project_summary": flatten_projects(yaml_data, body_sections),
        "linkedin_url": yaml_data.get("linkedin_url", "") or "",
        "github_url": yaml_data.get("github_url", "") or "",
        "email": yaml_data.get("email", "") or "",
        "status": yaml_data.get("status", "unknown"),
        "outreach_status": "not_contacted",
        "outreach_date": "",
        "last_updated_at": str(yaml_data.get("last_updated", datetime.now().strftime("%Y-%m-%d"))),
    }
    
    # Clean None values
    for key in row:
        if row[key] is None:
            row[key] = ""
    
    return row


def main():
    print(f"=== Obsidian → CSV Migration ===")
    print(f"Source: {CANDIDATES_DIR}")
    print(f"Output: {OUTPUT_FILE}")
    print()
    
    if not CANDIDATES_DIR.exists():
        print(f"ERROR: Candidates directory not found: {CANDIDATES_DIR}")
        return
    
    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # Process all candidate directories
    rows = []
    candidate_dirs = sorted([d for d in CANDIDATES_DIR.iterdir() if d.is_dir() and not d.name.startswith(".")])
    
    print(f"Found {len(candidate_dirs)} candidate directories")
    print()
    
    for cdir in candidate_dirs:
        print(f"Processing: {cdir.name}")
        row = process_candidate(cdir)
        if row:
            rows.append(row)
            print(f"  ✓ {row['name']} — {row['seniority']} — {row['location']}")
        else:
            print(f"  ✗ Skipped")
    
    print()
    print(f"=== Writing CSV ===")
    print(f"Total candidates: {len(rows)}")
    
    # Write CSV
    with open(OUTPUT_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"✓ Written to: {OUTPUT_FILE}")
    
    # Print summary stats
    print()
    print("=== Summary ===")
    seniority_counts = {}
    for row in rows:
        s = row["seniority"] or "unknown"
        seniority_counts[s] = seniority_counts.get(s, 0) + 1
    
    for s, count in sorted(seniority_counts.items()):
        print(f"  {s}: {count}")
    
    with_linkedin = sum(1 for r in rows if r["linkedin_url"])
    with_github = sum(1 for r in rows if r["github_url"])
    with_email = sum(1 for r in rows if r["email"])
    print(f"  With LinkedIn: {with_linkedin}")
    print(f"  With GitHub: {with_github}")
    print(f"  With Email: {with_email}")


if __name__ == "__main__":
    main()
