import openai
import time
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


class AISimplifier:
    def __init__(self):
        # A API key já está configurada nas variáveis de ambiente
        try:
            self.client = openai.OpenAI()
        except Exception:
            logger.exception('Falha inicializando cliente OpenAI')
            self.client = None

        # Definir prompts para cada nível de simplificação
        self.prompts: Dict[int, Dict[str, str]] = {
            1: {
                "name": "Muito Simples",
                "system": (
                    "Você é um especialista em simplificação de textos. Sua tarefa é reescrever textos literários mantendo "
                    "a história, personagens e eventos principais, mas usando linguagem muito simples e acessível.\n\n"
                    "Diretrizes: - Use frases curtas e diretas - Substitua palavras difíceis por sinônimos mais simples "
                    "- Mantenha todos os personagens, diálogos e eventos principais - Use vocabulário do dia a dia"
                ),
                "user": "Reescreva este trecho de narrativa mantendo personagens, ambientação e acontecimentos principais, mas com linguagem muito simples e frases curtas:\n\n{text}"
            },
            2: {
                "name": "Médio",
                "system": (
                    "Você é um especialista em simplificação de textos. Sua tarefa é reescrever textos literários mantendo "
                    "a história, personagens e eventos principais, mas usando linguagem clara e acessível, preservando parte da riqueza literária."
                ),
                "user": "Reescreva este trecho de narrativa mantendo personagens, ambientação e acontecimentos principais, mas com linguagem clara e acessível, preservando parte da riqueza literária:\n\n{text}"
            },
            3: {
                "name": "Comum",
                "system": (
                    "Você é um especialista em edição de textos. Sua tarefa é fazer pequenos ajustes em textos literários para melhorar a fluidez e clareza, mantendo quase toda a riqueza original."
                ),
                "user": "Faça pequenos ajustes neste trecho de narrativa para melhorar a fluidez e clareza, mantendo quase toda a riqueza literária original:\n\n{text}"
            }
        }

    def simplify_text(self, text: str, level: int) -> str:
        """Simplifica um texto usando IA baseado no nível especificado"""
        if level not in self.prompts:
            raise ValueError(f"Nível {level} não é válido. Use 1, 2 ou 3.")

        prompt_config = self.prompts[level]

        if not self.client:
            logger.warning('Cliente OpenAI não configurado; retornando texto original')
            return text

        try:
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": prompt_config["system"]},
                    {"role": "user", "content": prompt_config["user"].format(text=text)}
                ],
                max_tokens=4000,
                temperature=0.3  # Baixa temperatura para consistência
            )

            simplified_text = response.choices[0].message.content.strip()
            return simplified_text

        except Exception:
            logger.exception('Erro na simplificação via OpenAI')
            return text

    def simplify_chunks(self, chunks: List[str], level: int, progress_callback=None) -> List[str]:
        """Simplifica uma lista de chunks de texto"""
        simplified_chunks: List[str] = []
        total_chunks = len(chunks)

        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:  # Pular chunks muito pequenos
                simplified_chunks.append(chunk)
                continue

            try:
                simplified = self.simplify_text(chunk, level)
                simplified_chunks.append(simplified)

                if progress_callback:
                    progress_callback(i + 1, total_chunks)

                time.sleep(0.5)

            except Exception:
                logger.exception('Erro ao processar chunk %s', i)
                simplified_chunks.append(chunk)

        return simplified_chunks

    def simplify_chapter(self, chapter_content: str, level: int, max_chunk_words: int = 1500) -> str:
        """Simplifica um capítulo inteiro dividindo em chunks"""
        words = chapter_content.split()
        chunks = [ ' '.join(words[i:i + max_chunk_words]) for i in range(0, len(words), max_chunk_words) ]

        simplified_chunks = self.simplify_chunks(chunks, level)
        simplified_chapter = ' '.join(simplified_chunks)

        return simplified_chapter

    def get_level_description(self, level: int) -> str:
        if level in self.prompts:
            return self.prompts[level]["name"]
        return "Nível desconhecido"


# Função utilitária para usar em outras partes do código
def create_simplifier():
    return AISimplifier()

