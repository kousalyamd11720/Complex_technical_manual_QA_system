from __future__ import annotations

import google.generativeai as genai


class GeminiClient:
    def __init__(self, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("Missing GEMINI_API_KEY")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name=model_name)

    def generate(self, prompt: str) -> str:
        response = self.model.generate_content(prompt)
        return response.text or ""
