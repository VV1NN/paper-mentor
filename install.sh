#!/usr/bin/env bash
# PaperMentor installer — symlinks the skill into ~/.claude/skills/

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_SKILLS_DIR="$HOME/.claude/skills"
SKILL_NAME="paper-survey"

SOURCE="$REPO_ROOT/skills/$SKILL_NAME"
TARGET="$CLAUDE_SKILLS_DIR/$SKILL_NAME"

echo ""
echo "PaperMentor installer"
echo "====================="
echo ""
echo "  Source: $SOURCE"
echo "  Target: $TARGET"
echo ""

if [ ! -d "$SOURCE" ]; then
  echo "ERROR: skill source directory not found: $SOURCE"
  exit 1
fi

mkdir -p "$CLAUDE_SKILLS_DIR"

if [ -e "$TARGET" ] || [ -L "$TARGET" ]; then
  if [ -L "$TARGET" ]; then
    current_link="$(readlink "$TARGET")"
    if [ "$current_link" = "$SOURCE" ]; then
      echo "Already installed (symlink matches). No action needed."
      exit 0
    fi
    echo "Existing symlink points elsewhere: $current_link"
  else
    echo "Existing directory at $TARGET (not a symlink)."
  fi

  read -r -p "Remove it and re-install? [y/N] " ans
  case "$ans" in
    y|Y|yes|YES)
      rm -rf "$TARGET"
      ;;
    *)
      echo "Aborted."
      exit 1
      ;;
  esac
fi

ln -s "$SOURCE" "$TARGET"
echo "Installed: $TARGET -> $SOURCE"

echo ""
echo "Next steps:"
echo "  1. (Optional) Create a personal override:"
echo "       cp \"$SOURCE/pm-config.local.json.example\" \"$SOURCE/pm-config.local.json\""
echo "       Edit the local file to set your Obsidian vault path."
echo ""
echo "  2. In Claude Code, try:"
echo "       論文調研 indirect prompt injection in LLM agents"
echo ""
echo "  3. To update in the future:"
echo "       cd $REPO_ROOT && git pull"
echo "     (no reinstall needed — symlink auto-picks up changes)"
echo ""
