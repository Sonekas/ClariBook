import os
import re
import logging
import time
from typing import Optional, Tuple, Dict

import requests


# ----------------------------------------------------------------------------
# Hugging Face Inference API client for text rewriting and summarization.
# This module centralizes prompt construction, API calling, basic validation,
# and retry logic for robustness in production workflows.
#
# Environment:
#   - Set HF_TOKEN with your Hugging Face access token.
#
# Model:
#   - meta-llama/Meta-Llama-3.1-8B-Instruct (instruct-tuned for rewriting)
#
# Parameters chosen for consistent, deterministic-ish behavior in rewriting:
#   - temperature: 0.3  (low for stability)
#   - top_p: 0.9        (nucleus sampling)
#   - repetition_penalty: 1.15 (discourage loops)
#   - max_new_tokens: 1200     (sufficient for chunk rewrite)
# ----------------------------------------------------------------------------

logger = logging.getLogger(__name__)

HF_API_URL = "https://api-inference.huggingface.co/models/meta-llama/Meta-Llama-3.1-8B-Instruct"
FAST_MODE = os.getenv("FAST_MODE", "0") == "1"
DEFAULT_PARAMS = {
    "temperature": 0.3,
    "top_p": 0.9,
    "repetition_penalty": 1.15,
    "max_new_tokens": 600 if FAST_MODE else 1200,
}


def _hf_headers() -> Dict[str, str]:
    token = os.getenv("HF_TOKEN", "").strip()
    if not token:
        raise RuntimeError("HF_TOKEN não definido no ambiente")
    return {"Authorization": f"Bearer {token}"}


def _request_inference(prompt: str, params: Optional[Dict] = None, timeout: int = 90) -> str:
    """Low-level call to Hugging Face Inference API with retries on HTTP errors.
    Returns generated text or raises an exception.
    """
    payload = {
        "inputs": prompt,
        "parameters": params or DEFAULT_PARAMS,
        "options": {"wait_for_model": True},
    }
    try:
        r = requests.post(HF_API_URL, headers=_hf_headers(), json=payload, timeout=timeout)
        if r.status_code >= 400:
            raise RuntimeError(f"HF API HTTP {r.status_code}: {r.text[:500]}")
        data = r.json()
        # Common HF responses: [{"generated_text": "..."}] or {"error": "..."}
        if isinstance(data, list) and data and isinstance(data[0], dict) and "generated_text" in data[0]:
            return str(data[0]["generated_text"]).strip()
        if isinstance(data, dict) and "generated_text" in data:
            return str(data["generated_text"]).strip()
        if isinstance(data, dict) and "error" in data:
            raise RuntimeError(f"HF API error: {data['error']}")
        # Fallback best-effort
        return str(data).strip()
    except Exception as e:
        logger.exception("Falha na chamada à HF Inference API: %s", e)
        raise


def _is_output_valid(text: str, min_chars: int = 200) -> bool:
    """Basic output validation:
    - minimum length
    - avoid obvious repetition loops
    """
    if not text or len(text) < min_chars:
        return False
    tokens = re.findall(r"\w+", text.lower())
    if not tokens:
        return False
    unique_ratio = len(set(tokens)) / max(1, len(tokens))
    if unique_ratio < 0.25:
        return False
    # detect repeated 6-gram loops
    n = 6
    grams = [" ".join(tokens[i:i + n]) for i in range(0, max(0, len(tokens) - n + 1))]
    freq = {}
    for g in grams:
        freq[g] = freq.get(g, 0) + 1
        if freq[g] >= 5:
            return False
    return True


def _level_instructions(level: str) -> str:
    """Returns instruction suffix tuned by simplification level.
    - leve: keep style, clarify terms when needed, short sentences
    - moderado: simplify phrasing more, keep details
    - agressivo: aggressively simplify vocabulary and structure but do not summarize
    """
    level = (level or "").strip().lower()
    if level in ("leve", "light"):
        return (
            "Nível: LEVE. Mantenha o estilo e todo o conteúdo. Reescreva com frases curtas, "
            "clareza, explicando termos difíceis entre parênteses quando necessário."
        )
    if level in ("moderado", "moderate"):
        return (
            "Nível: MODERADO. Mantenha todo o conteúdo e exemplos, mas simplifique a redação "
            "e a ordem das frases para máxima clareza, sem resumir."
        )
    # agressivo (default)
    return (
        "Nível: AGRESSIVO. Mantenha todo o conteúdo e detalhes, porém simplifique vocabulário "
        "e estrutura de forma firme, sem resumir; preserve nomes, datas e números."
    )


def _build_rewrite_prompt(
    text_block: str,
    global_summary: str,
    chapter_summary: str,
    previous_output_tail: str,
    level: str,
) -> str:
    """Builds a professional instruction prompt mixing global+chapter context and local memory."""
    level_text = _level_instructions(level)
    return (
        "Você é um assistente editorial especializado em reescrita SEM RESUMIR.\n"
        "Siga as instruções com atenção. Preserve todos os fatos, nomes, datas, exemplos e estrutura lógica.\n\n"
        f"{level_text}\n"
        "Regras:\n"
        "1) NÃO resuma; mantenha o comprimento similar ao original.\n"
        "2) Preserve parágrafos; evite criar ou remover quebras desnecessárias.\n"
        "3) Ajuste frases para clareza, sem apagar conteúdo.\n"
        "4) Mantenha coerência com o que já foi reescrito (memória anterior).\n\n"
        "Contexto Global (resumo do livro):\n"
        f"{global_summary}\n\n"
        "Contexto do Capítulo (resumo):\n"
        f"{chapter_summary}\n\n"
        "Memória anterior (último trecho reescrito):\n"
        f"{previous_output_tail}\n\n"
        "Texto a reescrever (mantenha conteúdo e comprimento; apenas simplifique a linguagem):\n"
        f"{text_block}\n\n"
        "Texto reescrito:"
    )


def _build_summary_prompt(text: str, scope: str = "geral") -> str:
    """Builds a concise summarization prompt (no hallucinations, preserve coverage)."""
    return (
        "Você é um assistente editorial. Gere um RESUMO OBJETIVO, NÃO AVALIATIVO, cobrindo todas as ideias-chave.\n"
        "Não invente fatos. Máximo de 15 linhas. Linguagem clara.\n\n"
        f"Escopo do resumo: {scope}\n\n"
        f"Texto:\n{text}\n\n"
        "Resumo:"
    )


def rewrite_with_context(
    text_block: str,
    global_summary: str,
    chapter_summary: str,
    previous_output_tail: str,
    level: str = "moderado",
    attempts: int = 3,
) -> str:
    """Main API used by the processor.
    - Builds a high-quality prompt
    - Calls HF Inference API
    - Validates output and retries up to `attempts`
    """
    prompt = _build_rewrite_prompt(
        text_block=text_block,
        global_summary=global_summary,
        chapter_summary=chapter_summary,
        previous_output_tail=previous_output_tail,
        level=level,
    )
    for i in range(max(1, attempts)):
        try:
            out = _request_inference(prompt, DEFAULT_PARAMS)
            if _is_output_valid(out):
                return out
            logger.warning("Saída inválida (tentativa %s/%s). Tamanho=%s", i + 1, attempts, len(out or ""))
        except Exception as e:
            logger.warning("Falha ao reescrever (tentativa %s/%s): %s", i + 1, attempts, e)
        time.sleep(0.8)
    # Fallback: return original block if model failed repeatedly.
    return text_block


def summarize_text(text: str, scope: str = "geral", max_tokens: int = 600) -> str:
    """Summarizes long text using the same model (smaller max tokens)."""
    if FAST_MODE and max_tokens > 300:
        max_tokens = 300
    params = {**DEFAULT_PARAMS, "max_new_tokens": max_tokens}
    prompt = _build_summary_prompt(text, scope=scope)
    try:
        out = _request_inference(prompt, params)
        # Light validation: require non-empty
        return out if out and len(out) > 50 else (text[:1000] + ("..." if len(text) > 1000 else ""))
    except Exception:
        # Fallback: truncated original
        return text[:1000] + ("..." if len(text) > 1000 else "")


def improve_transitions(rewritten_chapter: str) -> str:
    """Second pass to smooth transitions between paragraphs/sentences without altering content."""
    prompt = (
        "Revise o texto abaixo APENAS para suavizar transições entre parágrafos e frases, "
        "sem remover conteúdo, sem resumir, sem introduzir novas ideias. "
        "Mantenha as mesmas informações e parágrafos.\n\n"
        f"Texto:\n{rewritten_chapter}\n\n"
        "Texto revisado:"
    )
    try:
        out = _request_inference(prompt, DEFAULT_PARAMS)
        return out if _is_output_valid(out, min_chars=max(100, int(len(rewritten_chapter) * 0.5))) else rewritten_chapter
    except Exception:
        return rewritten_chapter


# -----------------------------------------------------------------------------
# Example usage (pseudo):
# from hf_simplifier import rewrite_with_context, summarize_text, improve_transitions
# gsum = summarize_text(big_book_text, scope="geral")
# csum = summarize_text(chapter_text, scope="capítulo")
# new_chunk = rewrite_with_context(chunk, gsum, csum, previous_tail, level="moderado")
# final_chapter = improve_transitions("\n\n".join(chunks_out))
# -----------------------------------------------------------------------------
