"""
Skill Loader — Discovers and loads SKILL.md files from the skills/ directory.
OpenClaw-style extensible skill system using markdown + YAML frontmatter.

Each skill is a folder under skills/ containing a SKILL.md file with:
  ---
  name: skill_name
  description: What this skill does
  tools:
    - tool_name_1
    - tool_name_2
  ---
  # Markdown instructions for the LLM
"""

import os
import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger("SkillLoader")


@dataclass
class Skill:
    """A loaded skill with metadata and instructions."""
    name: str
    description: str
    tools: List[str]
    instructions: str  # The markdown body
    path: str          # Path to the SKILL.md file
    enabled: bool = True

    def get_prompt_section(self) -> str:
        """Format this skill as a section for the LLM system prompt."""
        tools_list = ", ".join(self.tools) if self.tools else "none"
        return (
            f"### Skill: {self.name}\n"
            f"**Description**: {self.description}\n"
            f"**Tools**: {tools_list}\n\n"
            f"{self.instructions}\n"
        )


class SkillLoader:
    """
    Discovers and loads skills from markdown files.
    
    Usage:
        loader = SkillLoader("skills/")
        loader.load_all()
        prompt = loader.get_skills_prompt()
    """

    def __init__(self, skills_dir: str = "skills"):
        self.skills_dir = os.path.abspath(skills_dir)
        self.skills: Dict[str, Skill] = {}
        self._load_count = 0

    def load_all(self) -> int:
        """Discover and load all skills from the skills directory."""
        if not os.path.isdir(self.skills_dir):
            logger.warning(f"Skills directory not found: {self.skills_dir}")
            os.makedirs(self.skills_dir, exist_ok=True)
            return 0

        loaded = 0
        for entry in os.listdir(self.skills_dir):
            skill_dir = os.path.join(self.skills_dir, entry)
            skill_file = os.path.join(skill_dir, "SKILL.md")
            
            if os.path.isdir(skill_dir) and os.path.isfile(skill_file):
                try:
                    skill = self._parse_skill(skill_file)
                    if skill:
                        self.skills[skill.name] = skill
                        loaded += 1
                        logger.info(f"✅ Loaded skill: {skill.name}")
                except Exception as e:
                    logger.error(f"❌ Failed to load skill from {skill_file}: {e}")

        self._load_count = loaded
        logger.info(f"📦 Loaded {loaded} skills from {self.skills_dir}")
        return loaded

    def _parse_skill(self, path: str) -> Optional[Skill]:
        """Parse a SKILL.md file into a Skill object."""
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse YAML frontmatter (between --- markers)
        frontmatter_match = re.match(
            r'^---\s*\n(.*?)\n---\s*\n(.*)$',
            content,
            re.DOTALL
        )

        if not frontmatter_match:
            logger.warning(f"No YAML frontmatter found in {path}")
            # Try loading as plain markdown
            name = os.path.basename(os.path.dirname(path))
            return Skill(
                name=name,
                description=f"Skill: {name}",
                tools=[],
                instructions=content.strip(),
                path=path,
            )

        yaml_text = frontmatter_match.group(1)
        body = frontmatter_match.group(2).strip()

        # Simple YAML parsing (no PyYAML dependency needed)
        metadata = self._parse_simple_yaml(yaml_text)

        name = metadata.get("name", os.path.basename(os.path.dirname(path)))
        description = metadata.get("description", f"Skill: {name}")
        tools = metadata.get("tools", [])

        return Skill(
            name=name,
            description=description,
            tools=tools if isinstance(tools, list) else [tools],
            instructions=body,
            path=path,
        )

    def _parse_simple_yaml(self, text: str) -> Dict[str, Any]:
        """Lightweight YAML parser for skill frontmatter (no dependency)."""
        result: Dict[str, Any] = {}
        current_key = None
        current_list: Optional[List[str]] = None

        for line in text.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Check for list item under current key
            if stripped.startswith("- ") and current_key:
                if current_list is None:
                    current_list = []
                current_list.append(stripped[2:].strip())
                result[current_key] = current_list
                continue

            # Key: value pair
            if ":" in stripped:
                # Save any pending list
                current_list = None

                key, _, value = stripped.partition(":")
                key = key.strip()
                value = value.strip()

                current_key = key
                if value:
                    result[key] = value
                # If value is empty, might be followed by a list
            else:
                current_list = None

        return result

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a specific skill by name."""
        return self.skills.get(name)

    def list_skills(self) -> List[Dict[str, Any]]:
        """List all loaded skills as dictionaries."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "tools": s.tools,
                "enabled": s.enabled,
                "path": s.path,
            }
            for s in self.skills.values()
        ]

    def get_skills_prompt(self) -> str:
        """
        Generate the skills section for the LLM system prompt.
        This is injected into the agent's system prompt so the LLM
        knows what skills and tools are available.
        """
        if not self.skills:
            return ""

        enabled = [s for s in self.skills.values() if s.enabled]
        if not enabled:
            return ""

        sections = ["## Available Skills\n"]
        sections.append(
            "You have the following skills available. "
            "Use the appropriate tools when the user's request matches a skill.\n"
        )

        for skill in enabled:
            sections.append(skill.get_prompt_section())

        return "\n".join(sections)

    def get_all_tools(self) -> List[str]:
        """Get a flat list of all tool names across all enabled skills."""
        tools = set()
        for skill in self.skills.values():
            if skill.enabled:
                tools.update(skill.tools)
        return sorted(tools)

    def enable_skill(self, name: str) -> bool:
        """Enable a skill by name."""
        skill = self.skills.get(name)
        if skill:
            skill.enabled = True
            return True
        return False

    def disable_skill(self, name: str) -> bool:
        """Disable a skill by name."""
        skill = self.skills.get(name)
        if skill:
            skill.enabled = False
            return True
        return False

    def reload(self) -> int:
        """Hot-reload: re-discover and re-load all skills."""
        self.skills.clear()
        return self.load_all()

    def add_skill_from_text(self, name: str, content: str) -> bool:
        """
        Create a new skill from markdown text at runtime.
        Writes a SKILL.md file and loads it immediately.
        """
        skill_dir = os.path.join(self.skills_dir, name)
        skill_file = os.path.join(skill_dir, "SKILL.md")

        try:
            os.makedirs(skill_dir, exist_ok=True)
            with open(skill_file, "w", encoding="utf-8") as f:
                f.write(content)

            skill = self._parse_skill(skill_file)
            if skill:
                self.skills[skill.name] = skill
                logger.info(f"✅ Created and loaded new skill: {name}")
                return True
        except Exception as e:
            logger.error(f"❌ Failed to create skill {name}: {e}")

        return False

    @property
    def count(self) -> int:
        """Number of loaded skills."""
        return len(self.skills)

    @property
    def enabled_count(self) -> int:
        """Number of enabled skills."""
        return sum(1 for s in self.skills.values() if s.enabled)

    def __repr__(self) -> str:
        return f"SkillLoader(skills={self.count}, enabled={self.enabled_count})"


# --- Quick test ---
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    loader = SkillLoader()
    n = loader.load_all()
    print(f"\nLoaded {n} skills:")
    for skill in loader.list_skills():
        print(f"  • {skill['name']}: {skill['description']}")
        print(f"    Tools: {', '.join(skill['tools'])}")
    print(f"\n--- System Prompt Section ---")
    print(loader.get_skills_prompt())
