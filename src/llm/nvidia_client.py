import json

import requests

from src.utils.config import Settings


class NvidiaLlamaClient:
    def __init__(self, settings: Settings):
        self.invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {settings.nvidia_api_key}",
            "Accept": "application/json",
        }
        self.model = settings.nvidia_model

    def chat(
        self,
        messages: list[dict],
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 1.0,
        stream: bool = False,
    ) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream,
        }
        response = requests.post(self.invoke_url, headers=self.headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()

    def stream_chat(
        self,
        messages: list[dict],
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 1.0,
    ):
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "stream": True,
        }
        response = requests.post(
            self.invoke_url, headers=self.headers, json=payload, stream=True, timeout=60
        )
        response.raise_for_status()
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                data = line[6:]
                if data.strip() == "[DONE]":
                    break
                try:
                    payload = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = payload.get("choices", [{}])[0].get("delta", {})
                content = delta.get("content", "")
                if content:
                    yield content
