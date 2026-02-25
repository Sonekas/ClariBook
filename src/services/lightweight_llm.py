import logging
import re
from typing import List, Dict

logger = logging.getLogger(__name__)


class LightweightLLMSimplifier:
    """Simplificador baseado em regras e padrões para ambientes com recursos limitados.
    Simula um LLM local usando técnicas de processamento de linguagem natural.
    """

    def __init__(self) -> None:
        self.device = "cpu"
        self.model_name = "lightweight-rule-based"

        # Dicionário de simplificação de palavras
        self.word_simplifications: Dict[str, str] = {
            "contemplar": "olhar",
            "observar": "ver",
            "perscrutar": "examinar",
            "vislumbrar": "ver",
            "avistar": "ver",
            "deparar": "encontrar",
            "deparar-se": "encontrar",
            "deparou": "encontrou",
            "contemplou": "olhou",
            "observou": "viu",
            "perscrutou": "examinou",
            "vislumbrou": "viu",
            "avistou": "viu",
            "magnifico": "lindo",
            "magnífico": "lindo",
            "esplêndido": "lindo",
            "formoso": "bonito",
            "belo": "bonito",
            "sublime": "incrível",
            "extraordinário": "incrível",
            "prodigioso": "incrível",
            "portentoso": "incrível",
            "assombrar": "impressionar",
            "maravilhar": "impressionar",
            "estupefazer": "impressionar",
            "pasmar": "impressionar",
            "embeveceu": "encantou",
            "arrebatou": "encantou",
            "extasiou": "encantou",
            "deslumbrou": "impressionou",
            "outrossim": "também",
            "ademais": "além disso",
            "destarte": "assim",
            "dessarte": "assim",
            "porquanto": "porque",
            "conquanto": "embora",
            "malgrado": "apesar de",
            "não obstante": "mesmo assim",
            "todavia": "mas",
            "contudo": "mas",
            "entretanto": "mas",
            "porém": "mas",
            "senão": "mas",
            "igualmente": "também",
            "semelhantemente": "da mesma forma",
            "analogamente": "da mesma forma",
        }

        # Padrões de simplificação sintática
        self.syntax_patterns = [
            (r'foi (\w+)do por', r'o \1'),
            (r'foram (\w+)dos por', r'os \1'),
            (r'era (\w+)do por', r'o \1'),
            (r'eram (\w+)dos por', r'os \1'),
            (r'estava (\w+)ndo', r'\1va'),
            (r'estavam (\w+)ndo', r'\1vam'),
            (r'há de (\w+)', r'vai \1'),
            (r'hão de (\w+)', r'vão \1'),
            (r'houve (\w+)', r'teve \1'),
            (r'houvera (\w+)', r'tinha \1'),
            (r'(\w+)-lhe', r'lhe \1'),
            (r'(\w+)-me', r'me \1'),
            (r'(\w+)-te', r'te \1'),
            (r'(\w+)-nos', r'nos \1'),
            (r'(\w+)-vos', r'vos \1'),
            (r'(\w+)-se', r'se \1'),
        ]

        # Prompts para cada nível (descrições apenas)
        self.prompts: Dict[int, Dict[str, str]] = {
            1: {"name": "Muito Simples", "description": "Frases curtas, vocabulário básico"},
            2: {"name": "Médio", "description": "Linguagem clara, mantendo elegância"},
            3: {"name": "Comum", "description": "Pequenos ajustes para fluidez"},
        }

        logger.info("Simplificador leve inicializado (baseado em regras)")

    def simplify_text(self, text: str, level: int) -> str:
        """Simplifica texto usando regras baseadas no nível"""
        if level not in [1, 2, 3]:
            raise ValueError(f"Nível {level} não é válido. Use 1, 2 ou 3.")

        simplified = text
        if level == 1:
            simplified = self._apply_heavy_simplification(simplified)
        elif level == 2:
            simplified = self._apply_medium_simplification(simplified)
        elif level == 3:
            simplified = self._apply_light_simplification(simplified)

        return simplified
    
    def _apply_heavy_simplification(self, text: str) -> str:
        """Aplica simplificação pesada (nível 1)"""
        result = text
        
        # Substituir palavras complexas (com espaçamento correto)
        for complex_word, simple_word in self.word_simplifications.items():
            # Usar word boundaries para evitar substituições parciais
            pattern = r'\b' + re.escape(complex_word) + r'\b'
            result = re.sub(pattern, simple_word, result, flags=re.IGNORECASE)
        
        # Aplicar padrões sintáticos
        for pattern, replacement in self.syntax_patterns:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Quebrar frases muito longas
        result = self._break_long_sentences(result, max_length=80)
        
        # Simplificar pontuação complexa
        result = self._simplify_punctuation(result)
        
        return result
    
    def _apply_medium_simplification(self, text: str) -> str:
        """Aplica simplificação média (nível 2)"""
        result = text
        
        # Aplicar apenas algumas substituições de palavras
        common_simplifications = {k: v for k, v in list(self.word_simplifications.items())[:len(self.word_simplifications)//2]}
        
        for complex_word, simple_word in common_simplifications.items():
            pattern = r'\b' + re.escape(complex_word) + r'\b'
            result = re.sub(pattern, simple_word, result, flags=re.IGNORECASE)
        
        # Aplicar alguns padrões sintáticos
        for pattern, replacement in self.syntax_patterns[:3]:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        # Quebrar apenas frases muito longas
        result = self._break_long_sentences(result, max_length=120)
        
        return result
    
    def _apply_light_simplification(self, text: str) -> str:
        """Aplica simplificação leve (nível 3)"""
        result = text
        
        # Aplicar apenas simplificações básicas
        basic_simplifications = {
            "outrossim": "também",
            "destarte": "assim",
            "porquanto": "porque",
            "não obstante": "mesmo assim",
            "todavia": "mas",
            "contudo": "mas",
            "entretanto": "mas"
        }
        
        for complex_word, simple_word in basic_simplifications.items():
            pattern = r'\b' + re.escape(complex_word) + r'\b'
            result = re.sub(pattern, simple_word, result, flags=re.IGNORECASE)
        
        # Aplicar apenas padrões básicos
        for pattern, replacement in self.syntax_patterns[:2]:
            result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)
        
        return result
    
    def _break_long_sentences(self, text: str, max_length: int = 100) -> str:
        """Quebra frases muito longas em frases menores"""
        sentences = re.split(r'[.!?]+', text)
        result_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) <= max_length or len(sentence) < 20:
                result_sentences.append(sentence)
            else:
                # Tentar quebrar em vírgulas ou pontos e vírgulas
                parts = re.split(r'[,;]+', sentence)
                current_part = ""
                
                for part in parts:
                    part = part.strip()
                    if len(current_part + part) <= max_length:
                        current_part += part + ", " if current_part else part
                    else:
                        if current_part:
                            result_sentences.append(current_part.rstrip(', '))
                        current_part = part
                
                if current_part:
                    result_sentences.append(current_part.rstrip(', '))
        
        # Reconstruir texto
        result = '. '.join([s for s in result_sentences if s.strip()])
        if result and not result.endswith(('.', '!', '?')):
            result += '.'
        
        return result
    
    def _simplify_punctuation(self, text: str) -> str:
        """Simplifica pontuação complexa"""
        # Substituir ponto e vírgula por ponto
        result = re.sub(r';', '.', text)
        
        # Substituir dois pontos seguidos de maiúscula por ponto
        result = re.sub(r':\s*([A-Z])', r'. \1', result)
        
        # Remover parênteses desnecessários
        result = re.sub(r'\([^)]*\)', '', result)
        
        # Limpar espaços duplos
        result = re.sub(r'\s+', ' ', result)
        
        return result.strip()
    
    def simplify_chunks(self, chunks: List[str], level: int, progress_callback=None) -> List[str]:
        """Simplifica uma lista de chunks"""
        simplified_chunks = []
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 20:  # Pular chunks muito pequenos
                simplified_chunks.append(chunk)
            else:
                simplified = self.simplify_text(chunk, level)
                simplified_chunks.append(simplified)
            
            # Callback para progresso
            if progress_callback:
                progress_callback(i + 1, total_chunks)
        
        return simplified_chunks
    
    def simplify_chapter(self, chapter_content: str, level: int, max_chunk_words: int = 1000) -> str:
        """Simplifica um capítulo dividindo em chunks"""
        # Dividir em parágrafos primeiro
        paragraphs = chapter_content.split('\n\n')
        simplified_paragraphs = []
        
        for paragraph in paragraphs:
            if len(paragraph.strip()) < 50:
                simplified_paragraphs.append(paragraph)
                continue
            
            # Se parágrafo for muito longo, dividir em chunks
            words = paragraph.split()
            if len(words) > max_chunk_words:
                chunks = []
                for i in range(0, len(words), max_chunk_words):
                    chunk = ' '.join(words[i:i + max_chunk_words])
                    chunks.append(chunk)
                
                simplified_chunks = self.simplify_chunks(chunks, level)
                simplified_paragraph = ' '.join(simplified_chunks)
            else:
                simplified_paragraph = self.simplify_text(paragraph, level)
            
            simplified_paragraphs.append(simplified_paragraph)
        
        return '\n\n'.join(simplified_paragraphs)
    
    def get_level_description(self, level: int) -> str:
        """Retorna descrição do nível"""
        if level in self.prompts:
            return self.prompts[level]["name"]
        return "Nível desconhecido"
    
    def get_model_info(self) -> Dict:
        """Retorna informações do modelo"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "model_loaded": True,
            "tokenizer_loaded": True,
            "pipeline_ready": True,
            "type": "rule-based"
        }

# Função para criar instância
def create_lightweight_simplifier():
    """Cria uma instância do simplificador leve"""
    return LightweightLLMSimplifier()

