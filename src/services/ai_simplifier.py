import openai
import os
import time
from typing import List, Dict

class AISimplifier:
    def __init__(self):
        # A API key já está configurada nas variáveis de ambiente
        self.client = openai.OpenAI()
        
        # Definir prompts para cada nível de simplificação
        self.prompts = {
            1: {
                "name": "Muito Simples",
                "system": """Você é um especialista em simplificação de textos. Sua tarefa é reescrever textos literários mantendo a história, personagens e eventos principais, mas usando linguagem muito simples e acessível.

Diretrizes:
- Use frases curtas e diretas
- Substitua palavras difíceis por sinônimos mais simples
- Mantenha todos os personagens, diálogos e eventos principais
- Use vocabulário do dia a dia
- Evite construções complexas ou subordinadas longas
- Mantenha o mesmo tempo verbal (passado, presente, etc.)
- Preserve a estrutura narrativa (início, meio, fim)""",
                "user": "Reescreva este trecho de narrativa mantendo personagens, ambientação e acontecimentos principais, mas com linguagem muito simples e frases curtas:\n\n{text}"
            },
            2: {
                "name": "Médio", 
                "system": """Você é um especialista em simplificação de textos. Sua tarefa é reescrever textos literários mantendo a história, personagens e eventos principais, mas usando linguagem clara e acessível, preservando parte da riqueza literária.

Diretrizes:
- Use linguagem clara mas mantenha alguma elegância
- Simplifique construções muito complexas
- Mantenha todos os personagens, diálogos e eventos principais
- Preserve descrições importantes mas simplifique-as
- Use vocabulário intermediário (nem muito simples, nem muito complexo)
- Mantenha o mesmo tempo verbal e estrutura narrativa
- Preserve o tom e atmosfera da obra original""",
                "user": "Reescreva este trecho de narrativa mantendo personagens, ambientação e acontecimentos principais, mas com linguagem clara e acessível, preservando parte da riqueza literária:\n\n{text}"
            },
            3: {
                "name": "Comum",
                "system": """Você é um especialista em edição de textos. Sua tarefa é fazer pequenos ajustes em textos literários para melhorar a fluidez e clareza, mantendo quase toda a riqueza original.

Diretrizes:
- Faça apenas pequenas simplificações para melhorar fluidez
- Mantenha a maior parte do vocabulário e estilo original
- Corrija apenas construções muito confusas ou arcaicas
- Preserve toda a riqueza literária possível
- Mantenha todos os personagens, diálogos e eventos
- Preserve descrições detalhadas e atmosfera
- Mantenha o mesmo tempo verbal e estrutura narrativa""",
                "user": "Faça pequenos ajustes neste trecho de narrativa para melhorar a fluidez e clareza, mantendo quase toda a riqueza literária original:\n\n{text}"
            }
        }
    
    def simplify_text(self, text: str, level: int) -> str:
        """Simplifica um texto usando IA baseado no nível especificado"""
        if level not in self.prompts:
            raise ValueError(f"Nível {level} não é válido. Use 1, 2 ou 3.")
        
        prompt_config = self.prompts[level]
        
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
            
        except Exception as e:
            print(f"Erro na simplificação: {str(e)}")
            # Em caso de erro, retornar texto original
            return text
    
    def simplify_chunks(self, chunks: List[str], level: int, progress_callback=None) -> List[str]:
        """Simplifica uma lista de chunks de texto"""
        simplified_chunks = []
        total_chunks = len(chunks)
        
        for i, chunk in enumerate(chunks):
            if len(chunk.strip()) < 50:  # Pular chunks muito pequenos
                simplified_chunks.append(chunk)
                continue
                
            try:
                simplified = self.simplify_text(chunk, level)
                simplified_chunks.append(simplified)
                
                # Callback para progresso
                if progress_callback:
                    progress_callback(i + 1, total_chunks)
                
                # Pequena pausa para evitar rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Erro ao processar chunk {i}: {str(e)}")
                simplified_chunks.append(chunk)  # Usar original em caso de erro
        
        return simplified_chunks
    
    def simplify_chapter(self, chapter_content: str, level: int, max_chunk_words: int = 1500) -> str:
        """Simplifica um capítulo inteiro dividindo em chunks"""
        # Dividir em chunks
        words = chapter_content.split()
        chunks = []
        
        for i in range(0, len(words), max_chunk_words):
            chunk = ' '.join(words[i:i + max_chunk_words])
            chunks.append(chunk)
        
        # Simplificar chunks
        simplified_chunks = self.simplify_chunks(chunks, level)
        
        # Juntar chunks simplificados
        simplified_chapter = ' '.join(simplified_chunks)
        
        return simplified_chapter
    
    def get_level_description(self, level: int) -> str:
        """Retorna descrição do nível de simplificação"""
        if level in self.prompts:
            return self.prompts[level]["name"]
        return "Nível desconhecido"

# Função utilitária para usar em outras partes do código
def create_simplifier():
    """Cria uma instância do simplificador"""
    return AISimplifier()

