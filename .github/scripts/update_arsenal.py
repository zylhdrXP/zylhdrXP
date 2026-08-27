#!/usr/bin/env python3
"""
Automatically fetch languages from GitHub repositories and update the
'Build Arsenal' section in README.md with Shields.io badges.
"""

import json
import os
import re
import sys
import urllib.request
import urllib.parse

# Known badge configurations for languages: (Badge Name, Background Color Hex, Logo Name, Logo Color)
# Reference: Shields.io badges using Simple Icons
LANGUAGE_BADGES = {
    "C": ("C", "A8B9CC", "c", "white"),
    "C++": ("C++", "00599C", "c%2B%2B", "white"),
    "C#": ("C%23", "239120", "c-sharp", "white"),
    "Shell": ("Shell_Script", "121011", "gnu-bash", "white"),
    "Bash": ("Bash", "4EAA25", "gnubash", "white"),
    "Python": ("Python", "3776AB", "python", "white"),
    "Kotlin": ("Kotlin", "7F52FF", "kotlin", "white"),
    "Java": ("Java", "ED8B00", "openjdk", "white"),
    "Makefile": ("Makefile", "064F8C", "gnu", "white"),
    "Rust": ("Rust", "000000", "rust", "white"),
    "Go": ("Go", "00ADD8", "go", "white"),
    "JavaScript": ("JavaScript", "F7DF1E", "javascript", "black"),
    "TypeScript": ("TypeScript", "3178C6", "typescript", "white"),
    "HTML": ("HTML5", "E34F26", "html5", "white"),
    "CSS": ("CSS3", "1572B6", "css3", "white"),
    "SCSS": ("SCSS", "CC6699", "sass", "white"),
    "PHP": ("PHP", "777BB4", "php", "white"),
    "Ruby": ("Ruby", "CC342D", "ruby", "white"),
    "Swift": ("Swift", "F05138", "swift", "white"),
    "Dart": ("Dart", "0175C2", "dart", "white"),
    "Lua": ("Lua", "2C2D72", "lua", "white"),
    "Assembly": ("Assembly", "6E4C13", "assemblyscript", "white"),
    "CMake": ("CMake", "064F8C", "cmake", "white"),
    "Dockerfile": ("Docker", "2496ED", "docker", "white"),
    "R": ("R", "276DC3", "r", "white"),
    "Perl": ("Perl", "39457E", "perl", "white"),
    "Scala": ("Scala", "DC322F", "scala", "white"),
    "Julia": ("Julia", "9558B2", "julia", "white"),
    "Haskell": ("Haskell", "5D4F85", "haskell", "white"),
    "Elixir": ("Elixir", "4B275F", "elixir", "white"),
    "Zig": ("Zig", "F7A41D", "zig", "black"),
    "Solidity": ("Solidity", "363636", "solidity", "white"),
    "Vue": ("Vue.js", "4FC08D", "vuedotjs", "white"),
    "Svelte": ("Svelte", "FF3E00", "svelte", "white"),
}

# Non-programming languages or metadata to ignore
IGNORED_LANGUAGES = {
    "AIDL", "SmPL", "Yacc", "Lex", "Roff", "M4", "Awk", "sed", "Gherkin", 
    "UnrealScript", "Linker Script", "Starlark", "Parrot", "XS", "Clojure"
}

def get_headers(token=None):
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Arsenal-Updater",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    return headers

def fetch_repos(username, token=None):
    repos = []
    page = 1
    while True:
        url = f"https://api.github.com/users/{username}/repos?per_page=100&page={page}"
        req = urllib.request.Request(url, headers=get_headers(token))
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if not data:
                    break
                repos.extend(data)
                if len(data) < 100:
                    break
                page += 1
        except Exception as e:
            print(f"Error fetching repos on page {page}: {e}", file=sys.stderr)
            break
    return repos

def fetch_languages(repos, token=None):
    language_counts = {}
    language_bytes = {}

    for repo in repos:
        # Tally primary language
        main_lang = repo.get("language")
        if main_lang and main_lang not in IGNORED_LANGUAGES:
            language_counts[main_lang] = language_counts.get(main_lang, 0) + 1

        # Optionally fetch language breakdown if token is provided
        lang_url = repo.get("languages_url")
        if token and lang_url:
            try:
                req = urllib.request.Request(lang_url, headers=get_headers(token))
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    for lang, byte_count in data.items():
                        if lang not in IGNORED_LANGUAGES:
                            language_bytes[lang] = language_bytes.get(lang, 0) + byte_count
            except Exception as e:
                pass

    # Prefer byte-based ranking if available, else repo count
    if language_bytes:
        ranked = sorted(language_bytes.items(), key=lambda x: x[1], reverse=True)
        return [lang for lang, _ in ranked]
    else:
        ranked = sorted(language_counts.items(), key=lambda x: x[1], reverse=True)
        return [lang for lang, _ in ranked]

def generate_badge_tag(lang_name):
    if lang_name in LANGUAGE_BADGES:
        label, color, logo, logo_color = LANGUAGE_BADGES[lang_name]
        alt = label.replace("%23", "#").replace("_", " ")
        return f'  <img alt="{alt}" src="https://img.shields.io/badge/{label}-{color}?style=for-the-badge&logo={logo}&logoColor={logo_color}" />'
    else:
        clean_label = urllib.parse.quote(lang_name)
        return f'  <img alt="{lang_name}" src="https://img.shields.io/badge/{clean_label}-333333?style=for-the-badge" />'

def update_readme(readme_path, badges):
    if not os.path.exists(readme_path):
        print(f"Error: {readme_path} not found.", file=sys.stderr)
        return False

    with open(readme_path, "r", encoding="utf-8") as f:
        content = f.read()

    arsenal_block = "<p align=\"center\">\n" + "\n".join(badges) + "\n</p>"

    # Check for START/END comments
    start_tag = "<!-- ARSENAL_START -->"
    end_tag = "<!-- ARSENAL_END -->"

    if start_tag in content and end_tag in content:
        pattern = re.compile(rf"{re.escape(start_tag)}[\s\S]*?{re.escape(end_tag)}")
        new_content = pattern.sub(f"{start_tag}\n{arsenal_block}\n{end_tag}", content)
    else:
        # Replace between ## 🛠️ Build Arsenal and the next ---
        pattern = re.compile(r"(## 🛠️ Build Arsenal\s*\n\n)([\s\S]*?)(\n\n---)")
        if pattern.search(content):
            new_content = pattern.sub(rf"\1{start_tag}\n{arsenal_block}\n{end_tag}\3", content)
        else:
            print("Error: Could not find 'Build Arsenal' section in README.md", file=sys.stderr)
            return False

    with open(readme_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print("Successfully updated README.md with latest languages.")
    return True

def main():
    username = os.environ.get("GITHUB_REPOSITORY_OWNER") or os.environ.get("GITHUB_ACTOR") or "zylhdrXP"
    token = os.environ.get("GITHUB_TOKEN")
    readme_path = os.environ.get("README_PATH", "README.md")

    print(f"Fetching GitHub repositories for user: {username}")
    repos = fetch_repos(username, token)
    print(f"Found {len(repos)} repositories.")

    languages = fetch_languages(repos, token)
    print(f"Detected languages: {languages}")

    if not languages:
        print("No languages detected. Keeping existing content.")
        return

    # Filter languages to recognizable ones or top 10
    top_languages = [l for l in languages if l in LANGUAGE_BADGES][:12]
    print(f"Selected top languages for arsenal: {top_languages}")

    badges = [generate_badge_tag(lang) for lang in top_languages]
    update_readme(readme_path, badges)

if __name__ == "__main__":
    main()
