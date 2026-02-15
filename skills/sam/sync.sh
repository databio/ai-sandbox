#!/bin/sh
rsync -av --delete --exclude='.DS_Store' --exclude='.git' --exclude='CLAUDE.md' --exclude='sync.sh' /Users/sam/.claude/skills/ /Users/sam/Documents/Work/ai-sandbox/skills/sam/
cp /Users/sam/.claude/CLAUDE.md /Users/sam/Documents/Work/ai-sandbox/skills/sam/CLAUDE.global.md
