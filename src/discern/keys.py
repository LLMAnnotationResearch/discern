"""API-key management.

Keys live in your ENVIRONMENT, or in a `.env` file OUTSIDE this repo — never committed. discern reads
one variable per provider and only the ones your configured model pool actually needs. The variable
name for each provider comes from the provider registry (discern.core.PROVIDERS); the built-ins are:

    OPENAI_API_KEY        # openai models (gpt-4o-mini, gpt-4.1-mini, gpt-4.1, ...)
    ANTHROPIC_API_KEY     # anthropic models (claude-haiku, ...)
    DEEPSEEK_API_KEY      # deepseek
    GEMINI_API_KEY        # gemini-flash (Google, OpenAI-compatible endpoint)
    OPENROUTER_API_KEY    # open-weight models via OpenRouter (llama-3.3-70b, qwen-2.5-72b, ...)
    TOGETHER_API_KEY / GROQ_API_KEY / FIREWORKS_API_KEY   # other OpenAI-compatible gateways

The built-in `local` provider is Ollama (default port, keyless); vLLM / LM-Studio or a remote server
need a custom provider with your own base_url. Any keyless provider needs no key; custom providers you
add in a config supply their own api_key_env (or null for keyless).

Recommended: keep keys in `~/.config/discern/.env` (chmod 600), which discern loads automatically.
Override the location with the DISCERN_ENV environment variable.
"""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_ENV = Path(os.environ.get("DISCERN_ENV", str(Path.home() / ".config" / "discern" / ".env")))


def load_env(path: Path = DEFAULT_ENV) -> None:
    """Load KEY=VALUE lines from a .env file into the environment, without overriding vars already
    set. Silently does nothing if the file is absent (env vars alone are fine)."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def required_providers(cfg) -> set[str]:
    """The set of providers a run with this config will actually call — derived from the shared
    active-model set (discovery + consolidation + measurement pool + theme model iff theming is on)."""
    from .core import MODELS
    return {MODELS[m][0] for m in cfg.active_models() if m in MODELS}


def missing_keys(cfg) -> list[str]:
    """Env-var names required by this config that are not currently set. Providers with no api_key_env
    (a keyless local server) are skipped."""
    from .core import PROVIDERS
    miss = []
    for p in sorted(required_providers(cfg)):
        env = PROVIDERS[p].api_key_env if p in PROVIDERS else None
        if env and not os.environ.get(env):
            miss.append(env)
    return miss


def check_or_raise(cfg) -> None:
    """Fail early with a friendly, specific message if any needed key is missing."""
    miss = missing_keys(cfg)
    if miss:
        raise SystemExit(
            f"Missing API key(s): {', '.join(miss)}\n\n"
            f"This run's model pool needs provider(s): {', '.join(sorted(required_providers(cfg)))}.\n"
            f"Set the variable(s) above in your environment, or add them to {DEFAULT_ENV} "
            f"(one KEY=VALUE per line). Run `discern setup-help` for step-by-step instructions.")


def setup_help() -> str:
    return f"""discern — API key setup

discern never stores keys in the repo. Put one variable per provider in the environment, or in a
.env file OUTSIDE the repo that discern loads automatically.

1. Create the config dir and file (recommended location):

     mkdir -p {DEFAULT_ENV.parent}
     touch {DEFAULT_ENV}
     chmod 600 {DEFAULT_ENV}

2. Add only the providers you plan to use, one per line:

     OPENAI_API_KEY=sk-...
     ANTHROPIC_API_KEY=sk-ant-...
     DEEPSEEK_API_KEY=sk-...
     GEMINI_API_KEY=...            # optional: gemini-flash
     OPENROUTER_API_KEY=sk-or-...  # optional: open-weight models (llama-3.3-70b, qwen-2.5-72b, ...)

   Get keys from: platform.openai.com/api-keys, console.anthropic.com, platform.deepseek.com,
   aistudio.google.com/apikey, openrouter.ai/keys (also together.ai / groq.com / fireworks.ai).
   A local model server (Ollama / vLLM / LM-Studio, the `local` provider) needs NO key.
   Run `discern models` to see every model/provider available and how to add your own.

3. That's it — `discern run ...` loads {DEFAULT_ENV} automatically. To use a different location:

     export DISCERN_ENV=/path/to/your.env

Alternatively, just export the variables in your shell; discern reads the environment directly and a
.env file is optional. discern only checks the providers your chosen models require."""
