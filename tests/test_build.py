"""Baseline tests for build.py — verify the build system works and generates expected output."""

import os
import re
import subprocess
import sys

import pytest


# --- Unit tests for helper functions ---


class TestRootPath:
    def test_depth_zero(self, build):
        assert build.root_path(0) == '.'

    def test_depth_one(self, build):
        assert build.root_path(1) == '..'

    def test_depth_two(self, build):
        assert build.root_path(2) == '../..'

    def test_depth_three(self, build):
        assert build.root_path(3) == '../../..'


class TestLoadConfig:
    def test_returns_dict(self, config):
        assert isinstance(config, dict)

    def test_has_required_keys(self, config):
        for key in ('team_name', 'github_url', 'course', 'semester', 'members'):
            assert key in config, f"config.json missing required key: {key}"

    def test_members_is_list(self, config):
        assert isinstance(config['members'], list)
        assert len(config['members']) > 0

    def test_member_has_required_fields(self, config):
        for member in config['members']:
            for field in ('name', 'email', 'bio'):
                assert field in member, f"Member missing required field: {field}"


class TestLoadRegistry:
    def test_returns_list(self, registry):
        assert isinstance(registry, list)

    def test_has_entries(self, registry):
        assert len(registry) > 0

    def test_entry_has_required_fields(self, registry):
        for lab in registry:
            for field in ('number', 'title', 'description'):
                assert field in lab, f"Lab entry missing required field: {field}"


class TestLoadPartials:
    def test_returns_dict(self, partials):
        assert isinstance(partials, dict)

    def test_has_expected_partials(self, partials):
        expected = ['HEAD', 'NAV', 'SIDEBAR', 'FOOTER']
        for name in expected:
            assert name in partials, f"Missing partial: {name}"

    def test_partials_are_nonempty(self, partials):
        for name, content in partials.items():
            assert len(content.strip()) > 0, f"Partial {name} is empty"


class TestGenerateTeamCards:
    def test_renders_member_with_photo(self, build):
        members = [{'name': 'Alice', 'email': 'a@mit.edu', 'photo': 'img/alice.jpg', 'bio': 'Hi'}]
        html = build.generate_team_cards(members, '.')
        assert 'team-card' in html
        assert 'img/alice.jpg' in html
        assert 'Alice' in html

    def test_renders_placeholder_without_photo(self, build):
        members = [{'name': 'Bob', 'email': 'b@mit.edu', 'photo': '', 'bio': 'Hey'}]
        html = build.generate_team_cards(members, '.')
        assert 'placeholder-headshot' in html
        assert 'fa-user' in html
        assert 'Bob' in html

    def test_empty_members(self, build):
        html = build.generate_team_cards([], '.')
        assert html == ''


class TestGenerateLatestLab:
    def test_with_labs(self, build, registry):
        html = build.generate_latest_lab(registry, '..')
        assert 'lab-card' in html
        assert registry[-1]['title'] in html

    def test_empty_registry(self, build):
        html = build.generate_latest_lab([], '..')
        assert 'Coming soon' in html

    def test_lab_without_thumbnail(self, build):
        labs = [{'number': 'lab1', 'title': 'Lab 1', 'description': 'Desc'}]
        html = build.generate_latest_lab(labs, '.')
        assert 'placeholder-lab-img' in html


class TestGenerateLabCards:
    def test_with_labs(self, build, registry):
        html = build.generate_lab_cards(registry, '.')
        assert 'lab-card' in html

    def test_empty_registry(self, build):
        html = build.generate_lab_cards([], '.')
        assert html == ''

    def test_lab_without_thumbnail(self, build):
        labs = [{'number': 'lab1', 'title': 'Lab 1', 'description': 'Desc'}]
        html = build.generate_lab_cards(labs, '.')
        assert 'placeholder-lab-img' in html
        assert 'lab1' in html

    def test_thumbnail_path_includes_root(self, build):
        labs = [{'number': 'lab1', 'title': 'Lab 1', 'description': 'Desc',
                 'thumbnail': 'img/test.jpg'}]
        html = build.generate_lab_cards(labs, '..')
        assert 'src="../img/test.jpg"' in html


class TestCharterUrl:
    def test_charter_url_in_config(self, config):
        """Verify config supports charter_url field."""
        assert 'charter_url' in config

    def test_generate_charter_link_with_url(self, build):
        """Charter link HTML is returned when URL is set."""
        cfg = {'charter_url': 'https://example.com/charter'}
        html = build.generate_charter_link(cfg)
        assert 'https://example.com/charter' in html
        assert 'Team Charter' in html
        assert 'target="_blank"' in html

    def test_generate_charter_link_empty(self, build):
        """Empty string returned when charter_url is empty."""
        assert build.generate_charter_link({'charter_url': ''}) == ''
        assert build.generate_charter_link({}) == ''


class TestDiscoverLabPages:
    def test_returns_list(self, build):
        pages = build.discover_lab_pages()
        assert isinstance(pages, list)

    def test_finds_example_lab(self, build):
        pages = build.discover_lab_pages()
        sources = [p[0] for p in pages]
        assert 'labs/example_lab/index.html' in sources

    def test_excludes_template(self, build):
        pages = build.discover_lab_pages()
        sources = [p[0] for p in pages]
        assert 'labs/_template/index.html' not in sources

    def test_depth_is_two(self, build):
        pages = build.discover_lab_pages()
        for _, _, depth in pages:
            assert depth == 2


# --- Integration tests: full build ---


EXPECTED_OUTPUT_FILES = [
    'index.html',
    'about/index.html',
    'labs/index.html',
    'labs/example_lab/index.html',
]


class TestFullBuild:
    def test_build_succeeds(self, root_dir):
        """Run build.py and verify it exits cleanly."""
        result = subprocess.run(
            [sys.executable, 'build.py'],
            cwd=root_dir,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Build failed:\n{result.stderr}"

    def test_expected_files_generated(self, root_dir):
        """Verify all expected output files exist after build."""
        # Run build first
        subprocess.run([sys.executable, 'build.py'], cwd=root_dir, capture_output=True)
        for rel_path in EXPECTED_OUTPUT_FILES:
            full_path = os.path.join(root_dir, rel_path)
            assert os.path.isfile(full_path), f"Missing output file: {rel_path}"

    def test_output_files_are_nonempty(self, root_dir):
        """Verify generated files have content."""
        subprocess.run([sys.executable, 'build.py'], cwd=root_dir, capture_output=True)
        for rel_path in EXPECTED_OUTPUT_FILES:
            full_path = os.path.join(root_dir, rel_path)
            size = os.path.getsize(full_path)
            assert size > 0, f"Output file is empty: {rel_path}"

    def test_no_unreplaced_template_variables(self, root_dir):
        """Verify no {{PLACEHOLDER}} variables remain in output."""
        subprocess.run([sys.executable, 'build.py'], cwd=root_dir, capture_output=True)
        import re
        for rel_path in EXPECTED_OUTPUT_FILES:
            full_path = os.path.join(root_dir, rel_path)
            with open(full_path, 'r') as f:
                content = f.read()
            matches = re.findall(r'\{\{[A-Z_]+\}\}', content)
            assert matches == [], f"Unreplaced variables in {rel_path}: {matches}"

    def test_root_paths_correct_depth0(self, root_dir):
        """Verify index.html uses '.' for root paths."""
        subprocess.run([sys.executable, 'build.py'], cwd=root_dir, capture_output=True)
        with open(os.path.join(root_dir, 'index.html'), 'r') as f:
            content = f.read()
        # Should contain './style.css' or similar depth-0 paths
        assert './style.css' in content
        # Should NOT contain '../style.css'
        assert '../style.css' not in content

    def test_root_paths_correct_depth1(self, root_dir):
        """Verify depth-1 pages use '..' for root paths."""
        subprocess.run([sys.executable, 'build.py'], cwd=root_dir, capture_output=True)
        with open(os.path.join(root_dir, 'about', 'index.html'), 'r') as f:
            content = f.read()
        assert '../style.css' in content

    def test_root_paths_correct_depth2(self, root_dir):
        """Verify depth-2 pages use '../..' for root paths."""
        subprocess.run([sys.executable, 'build.py'], cwd=root_dir, capture_output=True)
        with open(os.path.join(root_dir, 'labs', 'example_lab', 'index.html'), 'r') as f:
            content = f.read()
        assert '../../style.css' in content

    def test_team_name_in_output(self, root_dir, config):
        """Verify team name appears in generated pages."""
        subprocess.run([sys.executable, 'build.py'], cwd=root_dir, capture_output=True)
        with open(os.path.join(root_dir, 'index.html'), 'r') as f:
            content = f.read()
        assert config['team_name'] in content

    def test_nav_present_in_all_pages(self, root_dir):
        """Verify navigation is present in all generated pages."""
        subprocess.run([sys.executable, 'build.py'], cwd=root_dir, capture_output=True)
        for rel_path in EXPECTED_OUTPUT_FILES:
            full_path = os.path.join(root_dir, rel_path)
            with open(full_path, 'r') as f:
                content = f.read()
            assert 'site-nav' in content, f"Nav missing from {rel_path}"

    def test_footer_present_in_all_pages(self, root_dir):
        """Verify footer is present in all generated pages."""
        subprocess.run([sys.executable, 'build.py'], cwd=root_dir, capture_output=True)
        for rel_path in EXPECTED_OUTPUT_FILES:
            full_path = os.path.join(root_dir, rel_path)
            with open(full_path, 'r') as f:
                content = f.read()
            assert 'site-footer' in content, f"Footer missing from {rel_path}"

    def test_build_date_in_output(self, root_dir):
        """Verify built pages contain a build date stamp."""
        subprocess.run([sys.executable, 'build.py'], cwd=root_dir, capture_output=True)
        for rel_path in EXPECTED_OUTPUT_FILES:
            full_path = os.path.join(root_dir, rel_path)
            with open(full_path, 'r') as f:
                content = f.read()
            assert re.search(r'Last updated \d{4}-\d{2}-\d{2}', content), \
                f"Build date missing from {rel_path}"
