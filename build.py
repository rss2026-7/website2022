#!/usr/bin/env python3
"""build.py — Assembles the RSS Team 7 website from templates and partials.

Usage:
    python3 build.py          Build all pages
    python3 build.py --clean  Remove generated output files

How to update the site:
    1. Edit files in _src/ and _partials/ (NOT the root HTML files)
    2. Run: python3 build.py
    3. Commit all changes and push to GitHub

How to add a new team member:
    1. Add their entry to _src/config.json under "members"
    2. Put their photo in img/ (or leave "photo" empty for placeholder)
    3. Run: python3 build.py

How to add a new lab:
    1. Copy _src/labs/_template/ to _src/labs/[LAB_NUMBER]/
       IMPORTANT: Use the lab number (e.g. lab3, lab4) as the folder name.
       Graders access labs at: https://rss2026-#.github.io/website/labs/[LAB_NUMBER]
    2. Edit _src/labs/[LAB_NUMBER]/index.html (follow the EDIT THIS comments)
    3. Add an entry to _src/labs/_registry.json
    4. Run: python3 build.py
"""

import json
import os
import sys
from datetime import datetime

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
PARTIALS_DIR = os.path.join(ROOT_DIR, '_partials')
SRC_DIR = os.path.join(ROOT_DIR, '_src')
CONFIG_PATH = os.path.join(SRC_DIR, 'config.json')
REGISTRY_PATH = os.path.join(SRC_DIR, 'labs', '_registry.json')

# Static pages: (source_path relative to _src, output_path relative to root, depth)
PAGES = [
    ('index.html', 'index.html', 0),
    ('about.html', 'about/index.html', 1),
    ('labs/index.html', 'labs/index.html', 1),
]


def load_partials():
    """Load all HTML partials from _partials/ directory."""
    partials = {}
    for entry in sorted(os.listdir(PARTIALS_DIR)):
        if not entry.endswith('.html'):
            continue
        name = entry[:-5].upper().replace('-', '_')
        with open(os.path.join(PARTIALS_DIR, entry), 'r') as f:
            partials[name] = f.read()
    return partials


def _load_json(path, description):
    """Load a JSON file with helpful error messages."""
    if not os.path.isfile(path):
        sys.exit(f'Missing required file: {path} ({description})')
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        sys.exit(f'Invalid JSON in {path}: {e}')


def load_config():
    """Load site-wide configuration from config.json."""
    return _load_json(CONFIG_PATH, 'site configuration')


def load_registry():
    """Load lab metadata from _registry.json."""
    return _load_json(REGISTRY_PATH, 'lab registry')


def root_path(depth):
    """Return the correct relative root path for a given depth."""
    if depth == 0:
        return '.'
    return '/'.join(['..'] * depth)


def generate_team_cards(members, root):
    """Generate HTML for team member cards."""
    cards = []
    for member in members:
        if member.get('photo'):
            img = (f'<img class="headshot" src="{root}/{member["photo"]}" '
                   f'alt="Photo of {member["name"]}">')
        else:
            img = (f'<div class="placeholder-headshot" role="img" '
                   f'aria-label="Placeholder photo for {member["name"]}">'
                   f'<i class="fa fa-user"></i></div>')
        card = (
            f'    <div class="team-card">\n'
            f'      {img}\n'
            f'      <h4>{member["name"]}</h4>\n'
            f'      <p class="email">{member["email"]}</p>\n'
            f'      <p class="bio">{member["bio"]}</p>\n'
            f'    </div>'
        )
        cards.append(card)
    return '\n'.join(cards)


def generate_latest_lab(labs, root):
    """Generate HTML for the latest lab highlight, or a 'Coming soon' placeholder."""
    if not labs:
        return '  <p class="coming-soon" style="color:var(--text-muted);">Coming soon — check back after our first lab!</p>'
    lab = labs[-1]
    thumbnail = lab.get('thumbnail', '')
    if thumbnail:
        img = f'<img src="{root}/{thumbnail}" alt="{lab["title"]} thumbnail">'
    else:
        img = (f'<div class="placeholder-lab-img" '
               f'data-lab-number="{lab["number"]}"></div>')
    return (
        f'  <div class="labs-grid" style="max-width:480px; margin:0 auto;">\n'
        f'    <div class="lab-card">\n'
        f'      {img}\n'
        f'      <div class="lab-card-body">\n'
        f'        <h3>{lab["title"]}</h3>\n'
        f'        <p>{lab["description"]}</p>\n'
        f'        <a href="{root}/labs/{lab["number"]}/" class="btn">'
        f'<i class="fa fa-info-circle"></i> More Info</a>\n'
        f'      </div>\n'
        f'    </div>\n'
        f'  </div>'
    )


def generate_lab_cards(labs, root='.'):
    """Generate HTML for lab cards from registry."""
    cards = []
    for lab in labs:
        thumbnail = lab.get('thumbnail', '')
        if thumbnail:
            img = f'<img src="{root}/{thumbnail}" alt="{lab["title"]} thumbnail">'
        else:
            img = (f'<div class="placeholder-lab-img" '
                   f'data-lab-number="{lab["number"]}"></div>')
        card = (
            f'    <!-- {lab["title"]} -->\n'
            f'    <div class="lab-card">\n'
            f'      {img}\n'
            f'      <div class="lab-card-body">\n'
            f'        <h3>{lab["title"]}</h3>\n'
            f'        <p>{lab["description"]}</p>\n'
            f'        <a href="{lab["number"]}" class="btn">'
            f'<i class="fa fa-info-circle"></i> More Info</a>\n'
            f'      </div>\n'
            f'    </div>'
        )
        cards.append(card)
    return '\n'.join(cards)


def generate_charter_link(config):
    """Generate HTML for the team charter link, or empty string if URL is not set."""
    url = config.get('charter_url', '').strip()
    if not url:
        return ''
    return (
        '<section class="section" style="text-align:center;">\n'
        '  <a href="' + url + '" class="btn" target="_blank" rel="noopener">'
        '<i class="fa fa-file-text"></i> Team Charter</a>\n'
        '</section>'
    )


def discover_lab_pages():
    """Auto-discover lab pages from _src/labs/*/index.html, excluding _template/."""
    lab_pages = []
    labs_src = os.path.join(SRC_DIR, 'labs')
    if not os.path.isdir(labs_src):
        return lab_pages
    for entry in sorted(os.listdir(labs_src)):
        if entry.startswith('_') or entry.startswith('.'):
            continue
        lab_index = os.path.join(labs_src, entry, 'index.html')
        if os.path.isfile(lab_index):
            lab_pages.append((
                f'labs/{entry}/index.html',
                f'labs/{entry}/index.html',
                2
            ))
    return lab_pages


def build_page(source_path, output_path, depth, partials, config, registry, build_date=''):
    """Build a single page from its source template."""
    src_file = os.path.join(SRC_DIR, source_path)
    out_file = os.path.join(ROOT_DIR, output_path)

    with open(src_file, 'r') as f:
        content = f.read()

    root = root_path(depth)

    # Replace partials
    for name, partial_content in partials.items():
        content = content.replace('{{' + name + '}}', partial_content)

    # Replace config variables
    replacements = {
        '{{TEAM_NAME}}': config['team_name'],
        '{{GITHUB_URL}}': config['github_url'],
        '{{COURSE}}': config['course'],
        '{{SEMESTER}}': config['semester'],
        '{{HERO_IMAGE}}': config.get('hero_image', 'img/mit.jpg'),
        '{{TAGLINE}}': config.get('tagline', ''),
        '{{BUILD_DATE}}': build_date,
    }
    for placeholder, value in replacements.items():
        content = content.replace(placeholder, value)

    # Replace auto-generated content
    content = content.replace('{{TEAM_CARDS}}', generate_team_cards(config['members'], root))
    content = content.replace('{{LAB_CARDS}}', generate_lab_cards(registry, root))
    content = content.replace('{{LATEST_LAB}}', generate_latest_lab(registry, root))
    content = content.replace('{{CHARTER_LINK}}', generate_charter_link(config))

    # Replace {{ROOT}} last (after partials and team cards that contain {{ROOT}})
    content = content.replace('{{ROOT}}', root)

    # Create output directory
    os.makedirs(os.path.dirname(out_file), exist_ok=True)

    with open(out_file, 'w') as f:
        f.write(content)

    return out_file


def clean():
    """Remove generated output files."""
    lab_pages = discover_lab_pages()
    all_pages = PAGES + lab_pages
    removed = []
    for _, output_path, _ in all_pages:
        out_file = os.path.join(ROOT_DIR, output_path)
        if os.path.exists(out_file):
            os.remove(out_file)
            removed.append(output_path)
    # Clean empty directories created by build
    for dirpath in ['about']:
        d = os.path.join(ROOT_DIR, dirpath)
        if os.path.isdir(d) and not os.listdir(d):
            os.rmdir(d)
            removed.append(f'{dirpath}/')
    print(f'Cleaned {len(removed)} files')
    for f in removed:
        print(f'  removed {f}')


def main():
    partials = load_partials()
    config = load_config()
    registry = load_registry()
    lab_pages = discover_lab_pages()
    build_date = datetime.now().strftime('%Y-%m-%d')

    if '--clean' in sys.argv:
        clean()
        return

    all_pages = PAGES + lab_pages
    built = []

    for source_path, output_path, depth in all_pages:
        src_file = os.path.join(SRC_DIR, source_path)
        if not os.path.exists(src_file):
            print(f'  SKIP {output_path} (source not found: _src/{source_path})')
            continue
        build_page(source_path, output_path, depth, partials, config, registry, build_date)
        built.append(output_path)

    print(f'Built {len(built)} pages:')
    for f in built:
        print(f'  {f}')


if __name__ == '__main__':
    main()
