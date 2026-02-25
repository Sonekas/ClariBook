import logging
import time
import gc
from typing import List, Dict

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline

logger = logging.getLogger(__name__)


class LocalLLMSimplifier:
    def __init__(self, model_name: str = "teknium/OpenHermes-2.5-Mistral-7B") -> None:
        """Inicializa o simplificador com modelo local."""
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        self.pipeline = None

        logger.info("Inicializando LLM local: %s (device=%s)", model_name, self.device)

        # Carregar modelo e tokenizer
        self._load_model()

        # Definir prompts para cada nível (mantido como antes)
        self.prompts: Dict[int, Dict[str, str]] = {
            1: {
                "name": "Muito Simples",
                "system": "...",
                "user": "Reescreva este trecho..."
            },
            2: {"name": "Médio", "system": "...", "user": "Reescreva este trecho..."},
            3: {"name": "Comum", "system": "...", "user": "Reescreva este trecho..."}
        }

    def _load_model(self) -> None:
        """Carrega o modelo e tokenizer"""
        try:
            logger.info("Carregando tokenizer para %s...", self.model_name)
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)

            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            logger.info("Carregando modelo %s...", self.model_name)
            model_kwargs = {
                "trust_remote_code": True,
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
                "device_map": "auto" if self.device == "cuda" else None,
            }

            if self.device == "cuda":
                try:
                    model_kwargs.update({
                        "load_in_4bit": True,
                        "bnb_4bit_compute_dtype": torch.float16,
                        "bnb_4bit_use_double_quant": True,
                        "bnb_4bit_quant_type": "nf4",
                    })
                except Exception:
                    logger.debug("Quantização 4-bit falhou; usando configuração padrão")

            self.model = AutoModelForCausalLM.from_pretrained(self.model_name, **model_kwargs)

            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device_map="auto" if self.device == "cuda" else None,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            )

            logger.info("Modelo carregado com sucesso")

        except Exception:
            logger.exception("Erro ao carregar modelo %s; tentando fallback", self.model_name)
            self._load_fallback_model()

    def _load_fallback_model(self) -> None:
        """Carrega um modelo menor como fallback"""
        try:
            fallback_model = "microsoft/DialoGPT-medium"
            logger.info("Carregando modelo fallback: %s", fallback_model)

            self.tokenizer = AutoTokenizer.from_pretrained(fallback_model)
            self.model = AutoModelForCausalLM.from_pretrained(fallback_model, torch_dtype=torch.float32)

            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.pipeline = pipeline("text-generation", model=self.model, tokenizer=self.tokenizer)
            logger.info("Modelo fallback carregado")
        except Exception:
            logger.exception("Erro crítico ao carregar modelo fallback")
            raise

    def _format_prompt(self, system_prompt: str, user_prompt: str) -> str:
        if "OpenHermes" in self.model_name:
            return f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"
        if "Mistral" in self.model_name:
            return f"<s>[INST] {system_prompt}\n\n{user_prompt} [/INST]"
        return f"System: {system_prompt}\n\nUser: {user_prompt}\n\nAssistant:"

    def simplify_text(self, text: str, level: int) -> str:
        if level not in self.prompts:
            raise ValueError(f"Nível {level} não é válido. Use 1, 2 ou 3.")

        if not self.pipeline:
            raise RuntimeError("Modelo não foi carregado corretamente")

        prompt_config = self.prompts[level]

        try:
            system_prompt = prompt_config["system"]
            user_prompt = prompt_config["user"].format(text=text)
            full_prompt = self._format_prompt(system_prompt, user_prompt)

            logger.debug("Gerando simplificação (nível %s)", level)
            start_time = time.time()

            generation_config = {
                "max_new_tokens": min(2048, max(32, len(text) * 2)),
                "temperature": 0.3,
                "do_sample": True,
                "top_p": 0.9,
                "top_k": 50,
                "repetition_penalty": 1.1,
                "pad_token_id": self.tokenizer.eos_token_id,
                "eos_token_id": self.tokenizer.eos_token_id,
                "return_full_text": False,
            }

            response = self.pipeline(full_prompt, **generation_config)
            end_time = time.time()
            logger.debug("Geração concluída em %.2fs", end_time - start_time)

            if response and len(response) > 0:
                simplified_text = response[0].get('generated_text', '').strip()
                if "<|im_end|>" in simplified_text:
                    simplified_text = simplified_text.split("<|im_end|>")[0]
                if "[/INST]" in simplified_text:
                    simplified_text = simplified_text.split("[/INST]")[-1]
                return simplified_text.strip() or text

            logger.warning("Resposta vazia do modelo; retornando texto original")
            return text

        except Exception:
            logger.exception("Erro na simplificação local")
            return text

    def simplify_chunks(self, chunks: List[str], level: int, progress_callback=None) -> List[str]:
        simplified_chunks: List[str] = []
        total_chunks = len(chunks)

        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:
                simplified_chunks.append(chunk)
            else:
                try:
                    simplified = self.simplify_text(chunk, level)
                    simplified_chunks.append(simplified)
                except Exception:
                    logger.exception('Erro ao processar chunk %s', i)
                    simplified_chunks.append(chunk)

            if progress_callback:
                progress_callback(i + 1, total_chunks)

            if i % 5 == 0:
                self._cleanup_memory()

        return simplified_chunks

    def simplify_chapter(self, chapter_content: str, level: int, max_chunk_words: int = 800) -> str:
        words = chapter_content.split()
        chunks = [ ' '.join(words[i:i + max_chunk_words]) for i in range(0, len(words), max_chunk_words) ]
        logger.info("Processando capítulo em %s chunks...", len(chunks))
        simplified_chunks = self.simplify_chunks(chunks, level)
        return ' '.join(simplified_chunks)

    def _cleanup_memory(self) -> None:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()

    def get_level_description(self, level: int) -> str:
        if level in self.prompts:
            return self.prompts[level]["name"]
        return "Nível desconhecido"

    def get_model_info(self) -> Dict:
        return {
            "model_name": self.model_name,
            "device": self.device,
            "model_loaded": self.model is not None,
            "tokenizer_loaded": self.tokenizer is not None,
            "pipeline_ready": self.pipeline is not None,
        }


def create_local_simplifier(model_name: str = "teknium/OpenHermes-2.5-Mistral-7B") -> LocalLLMSimplifier:
    return LocalLLMSimplifier(model_name)

