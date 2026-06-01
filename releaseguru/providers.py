import os


def call_groq(prompt: str, api_key: str | None = None, model: str | None = None) -> str:
    from groq import Groq

    key = api_key or os.environ.get("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY not found in environment or passed as argument.")

    client = Groq(api_key=key)
    response = client.chat.completions.create(
        model=model or "llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    return response.choices[0].message.content


def call_openai(prompt: str, api_key: str | None = None, model: str | None = None) -> str:
    from openai import OpenAI

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise ValueError("OPENAI_API_KEY not found in environment or passed as argument.")

    client = OpenAI(api_key=key)
    response = client.chat.completions.create(
        model=model or "gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    return response.choices[0].message.content


def call_anthropic(prompt: str, api_key: str | None = None, model: str | None = None) -> str:
    import anthropic

    key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise ValueError("ANTHROPIC_API_KEY not found in environment or passed as argument.")

    client = anthropic.Anthropic(api_key=key)
    response = client.messages.create(
        model=model or "claude-3-5-haiku-20241022",
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def call_gemini(prompt: str, api_key: str | None = None, model: str | None = None) -> str:
    import google.generativeai as genai

    key = api_key or os.environ.get("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY not found in environment or passed as argument.")

    genai.configure(api_key=key)
    model_instance = genai.GenerativeModel(model or "gemini-1.5-flash")
    response = model_instance.generate_content(prompt)
    return response.text


def call_xai(prompt: str, api_key: str | None = None, model: str | None = None) -> str:
    from openai import OpenAI

    key = api_key or os.environ.get("XAI_API_KEY")
    if not key:
        raise ValueError("XAI_API_KEY not found in environment or passed as argument.")

    client = OpenAI(api_key=key, base_url="https://api.x.ai/v1")
    response = client.chat.completions.create(
        model=model or "grok-3-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    return response.choices[0].message.content


PROVIDERS = {
    "groq": call_groq,
    "openai": call_openai,
    "anthropic": call_anthropic,
    "gemini": call_gemini,
    "xai": call_xai,
}


def auto_detect_provider() -> str:
    for name, key in [
        ("groq", "GROQ_API_KEY"),
        ("gemini", "GEMINI_API_KEY"),
        ("openai", "OPENAI_API_KEY"),
        ("anthropic", "ANTHROPIC_API_KEY"),
        ("xai", "XAI_API_KEY"),
    ]:
        if os.environ.get(key):
            return name

    raise EnvironmentError(
        "No API key found. Set one of: GROQ_API_KEY, GEMINI_API_KEY, "
        "OPENAI_API_KEY, ANTHROPIC_API_KEY, or XAI_API_KEY in your .env, "
        "or pass a custom key via --api-key."
    )
