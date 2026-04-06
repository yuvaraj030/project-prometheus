import os
import time
import uuid
import webbrowser
from typing import Dict, Any

class GenerativeUI:
    """
    Renders dynamic, generative HTML/CSS/JS dashboards based on LLM output.
    Allows the agent to create temporary web UIs on the fly for complex data visualization.
    """
    def __init__(self, llm_provider, output_dir="temp_ui"):
        self.llm = llm_provider
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_dashboard(self, prompt: str, data: Dict[str, Any] = None) -> str:
        """
        Asks the LLM to generate a single-file interactive HTML dashboard.
        Saves it to a temp file and opens it in the browser.
        """
        print(f"  🎨 Generating Dynamic UI for: '{prompt}'...")
        
        system_prompt = (
            "You are an expert Frontend Developer and UI/UX Designer. "
            "Your task is to generate a complete, working HTML file with embedded CSS and JavaScript. "
            "The design MUST be modern, beautiful, and dynamic (use glassmorphism, gradients, hover effects, "
            "and animations). Do NOT output Markdown code blocks (```html). Just output the raw HTML text "
            "starting with <!DOCTYPE html>."
        )
        
        data_context = f"\n\nInject this data into the visualization if possible:\n{data}" if data else ""
        
        full_prompt = (
            f"Generate a single-file HTML dashboard for the following request:\n"
            f"{prompt}\n"
            f"{data_context}\n\n"
            "Requirements:\n"
            "- Include Chart.js via CDN if graphs are needed.\n"
            "- Include modern fonts (Google Fonts).\n"
            "- Make it responsive.\n"
            "- It must look like a premium SaaS dashboard.\n"
        )
        
        html_content = self.llm.call(full_prompt, system=system_prompt, max_tokens=3000, temperature=0.7)
        
        # Clean up any trailing/leading markdown if the LLM hallucinated it
        if "```html" in html_content:
            html_content = html_content.split("```html")[1]
        if "```" in html_content:
            html_content = html_content.split("```")[0]
            
        return self._render_and_open(html_content.strip())

    def _render_and_open(self, html_content: str) -> str:
        """Saves the HTML to a file and opens it."""
        filename = f"dashboard_{uuid.uuid4().hex[:8]}.html"
        filepath = os.path.abspath(os.path.join(self.output_dir, filename))
        
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)
            
        print(f"  ✅ UI Generated Successfully. Rendering {filename}...")
        webbrowser.open(f"file:///{filepath}")
        return filepath
