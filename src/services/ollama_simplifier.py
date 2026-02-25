import os
import requests
from typing import Optional
import subprocess
import time
import shutil
import logging

logger = logging.getLogger(__name__)


class OllamaSimplifier:
    def __init__(self, host: Optional[str] = None, model: Optional[str] = None, timeout: int = 120):
        self.host = (host or os.getenv('OLLAMA_HOST') or 'http://localhost:11434').rstrip('/')
        self.model = model or os.getenv('OLLAMA_MODEL') or 'gemma:2b'
        self.timeout = timeout

    def is_available(self) -> bool:
        try:
            r = requests.get(self.host + '/', timeout=3)
            if r.status_code == 200:
                return True
        except Exception:
            logger.debug('Ollama ping falhou para %s', self.host)
        try:
            r = requests.get(self.host + '/api/tags', timeout=3)
            return r.status_code == 200
        except Exception:
            logger.debug('Consulta /api/tags falhou para %s', self.host)
            return False

    def ensure_available(self) -> bool:
        try:
            if self.is_available():
                return True
            if shutil.which("ollama") is None:
                logger.warning('Comando ollama não encontrado; não é possível iniciar servidor')
                return False
            try:
                subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False,
                                 creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            except Exception:
                try:
                    subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    logger.exception('Falha ao iniciar comando ollama')
                    return False
            for _ in range(10):
                time.sleep(0.6)
                if self.is_available():
                    return True
            return False
        except Exception:
            logger.exception('Erro em ensure_available')
            return False

    def _build_prompt(self, text: str, level: int, preserve_structure: bool = False) -> str:
        level_instructions = {
            1: (
                "Reescreva o texto abaixo em pt-BR com linguagem simples e clara, SEM RESUMIR e SEM REMOVER informação."
                " Mantenha o COMPRIMENTO semelhante ao original e preserve todos os nomes, datas, citações e detalhes."
                " Use frases curtas e diretas."
            ),
            2: (
                "Reescreva o texto abaixo em pt-BR de forma mais clara e acessível, SEM RESUMIR nem omitir informações."
                " Mantenha o comprimento próximo ao original e preserve estrutura, exemplos e detalhes."
                " Simplifique a redação sem reduzir conteúdo."
            ),
            3: (
                "Melhore levemente a clareza do texto abaixo em pt-BR, SEM RESUMIR e mantendo o estilo, nuances e comprimento."
                " Apenas reescreva trechos confusos, preservando a estrutura original e todo o conteúdo."
            ),
        }
        suffix = (
            " IMPORTANTE: Preserve exatamente a estrutura e pontuação. NÃO junte nem quebre parágrafos."
            " Se o texto de entrada for um único parágrafo, devolva um ÚNICO parágrafo."
            " Não altere sinais de pontuação desnecessariamente; apenas simplifique vocabulário."
        ) if preserve_structure else (
            " Preserve a estrutura e os parágrafos sempre que possível."
        )
        instruction = level_instructions.get(level, level_instructions[3]) + suffix
        return f"{instruction}\n\nTexto original:\n{text}\n\nTexto simplificado:"

    def simplify_text(self, text: str, level: int, preserve_structure: bool = False) -> str:
        payload = {
            'model': self.model,
            'prompt': self._build_prompt(text, level, preserve_structure=preserve_structure),
            'stream': False,
            'options': {'temperature': 0.4}
        }
        url = f"{self.host}/api/generate"
        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get('response', text).strip() or text
        except Exception:
            logger.exception('Erro simplificando via Ollama')
            return text


def create_ollama_simplifier(host: Optional[str] = None, model: Optional[str] = None) -> OllamaSimplifier:
    return OllamaSimplifier(host=host, model=model)