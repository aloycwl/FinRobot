from __future__ import annotations

from openai import OpenAI

from .config import settings


def llm_prediction(prompt: str, system_prompt: str) -> str:
    if not settings.nvidia_key:
        return "NVIDIA key missing. Set NV in environment to use LLM prediction."

    client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=settings.nvidia_key)
    result = client.chat.completions.create(
        model=settings.nvidia_model,
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": prompt}],
        temperature=0.2,
        top_p=0.7,
        max_tokens=2048,
        extra_body={"chat_template_kwargs": {"thinking": False}},
        stream=False,
    )
    return result.choices[0].message.content or ""
