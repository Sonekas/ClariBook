import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import time
from typing import List, Dict
import gc
import os

class LocalLLMSimplifier:
    def __init__(self, model_name="teknium/OpenHermes-2.5-Mistral-7B"):
        """
        Inicializa o simplificador com modelo local
        
        Args:
            model_name: Nome do modelo no HuggingFace Hub
                       Opções: "teknium/OpenHermes-2.5-Mistral-7B" ou "mistralai/Mistral-7B-Instruct-v0.3"
        """
        self.model_name = model_name
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        self.pipeline = None
        
        print(f"Inicializando LLM local: {model_name}")
        print(f"Dispositivo: {self.device}")
        
        # Carregar modelo e tokenizer
        self._load_model()
        
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
    
    def _load_model(self):
        """Carrega o modelo e tokenizer"""
        try:
            print("Carregando tokenizer...")
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                trust_remote_code=True
            )
            
            # Configurar pad_token se não existir
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            print("Carregando modelo...")
            # Configurações para otimizar uso de memória
            model_kwargs = {
                "trust_remote_code": True,
                "torch_dtype": torch.float16 if self.device == "cuda" else torch.float32,
                "device_map": "auto" if self.device == "cuda" else None,
            }
            
            # Adicionar quantização se disponível
            if self.device == "cuda":
                try:
                    model_kwargs["load_in_4bit"] = True
                    model_kwargs["bnb_4bit_compute_dtype"] = torch.float16
                    model_kwargs["bnb_4bit_use_double_quant"] = True
                    model_kwargs["bnb_4bit_quant_type"] = "nf4"
                except:
                    # Se quantização falhar, usar configuração padrão
                    model_kwargs = {
                        "trust_remote_code": True,
                        "torch_dtype": torch.float16,
                        "device_map": "auto",
                    }
            
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                **model_kwargs
            )
            
            # Criar pipeline de geração
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device_map="auto" if self.device == "cuda" else None,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            )
            
            print("Modelo carregado com sucesso!")
            
        except Exception as e:
            print(f"Erro ao carregar modelo: {str(e)}")
            # Fallback para modelo menor se houver erro
            print("Tentando carregar modelo menor...")
            self._load_fallback_model()
    
    def _load_fallback_model(self):
        """Carrega um modelo menor como fallback"""
        try:
            fallback_model = "microsoft/DialoGPT-medium"
            print(f"Carregando modelo fallback: {fallback_model}")
            
            self.tokenizer = AutoTokenizer.from_pretrained(fallback_model)
            self.model = AutoModelForCausalLM.from_pretrained(
                fallback_model,
                torch_dtype=torch.float32
            )
            
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=self.device
            )
            
            print("Modelo fallback carregado!")
            
        except Exception as e:
            print(f"Erro crítico ao carregar modelo: {str(e)}")
            raise e
    
    def _format_prompt(self, system_prompt: str, user_prompt: str) -> str:
        """Formata o prompt para o modelo"""
        if "OpenHermes" in self.model_name:
            # Formato ChatML para OpenHermes
            return f"<|im_start|>system\n{system_prompt}<|im_end|>\n<|im_start|>user\n{user_prompt}<|im_end|>\n<|im_start|>assistant\n"
        elif "Mistral" in self.model_name:
            # Formato Mistral
            return f"<s>[INST] {system_prompt}\n\n{user_prompt} [/INST]"
        else:
            # Formato genérico
            return f"System: {system_prompt}\n\nUser: {user_prompt}\n\nAssistant:"
    
    def simplify_text(self, text: str, level: int) -> str:
        """Simplifica um texto usando o modelo local"""
        if level not in self.prompts:
            raise ValueError(f"Nível {level} não é válido. Use 1, 2 ou 3.")
        
        if not self.pipeline:
            raise RuntimeError("Modelo não foi carregado corretamente")
        
        prompt_config = self.prompts[level]
        
        try:
            # Formatar prompt
            system_prompt = prompt_config["system"]
            user_prompt = prompt_config["user"].format(text=text)
            full_prompt = self._format_prompt(system_prompt, user_prompt)
            
            # Configurações de geração
            generation_config = {
                "max_new_tokens": min(2048, len(text) * 2),  # Limitar tokens baseado no texto
                "temperature": 0.3,
                "do_sample": True,
                "top_p": 0.9,
                "top_k": 50,
                "repetition_penalty": 1.1,
                "pad_token_id": self.tokenizer.eos_token_id,
                "eos_token_id": self.tokenizer.eos_token_id,
                "return_full_text": False
            }
            
            # Gerar resposta
            print(f"Gerando simplificação (nível {level})...")
            start_time = time.time()
            
            response = self.pipeline(
                full_prompt,
                **generation_config
            )
            
            end_time = time.time()
            print(f"Geração concluída em {end_time - start_time:.2f}s")
            
            # Extrair texto simplificado
            if response and len(response) > 0:
                simplified_text = response[0]['generated_text'].strip()
                
                # Limpar possíveis artefatos do prompt
                if "<|im_end|>" in simplified_text:
                    simplified_text = simplified_text.split("<|im_end|>")[0]
                if "[/INST]" in simplified_text:
                    simplified_text = simplified_text.split("[/INST]")[-1]
                
                return simplified_text.strip()
            else:
                print("Erro: Resposta vazia do modelo")
                return text  # Retornar texto original em caso de erro
                
        except Exception as e:
            print(f"Erro na simplificação: {str(e)}")
            return text  # Retornar texto original em caso de erro
    
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
                
                # Limpeza de memória a cada 5 chunks
                if i % 5 == 0:
                    self._cleanup_memory()
                
            except Exception as e:
                print(f"Erro ao processar chunk {i}: {str(e)}")
                simplified_chunks.append(chunk)  # Usar original em caso de erro
        
        return simplified_chunks
    
    def simplify_chapter(self, chapter_content: str, level: int, max_chunk_words: int = 800) -> str:
        """Simplifica um capítulo inteiro dividindo em chunks menores"""
        # Dividir em chunks menores para modelos locais
        words = chapter_content.split()
        chunks = []
        
        for i in range(0, len(words), max_chunk_words):
            chunk = ' '.join(words[i:i + max_chunk_words])
            chunks.append(chunk)
        
        print(f"Processando capítulo em {len(chunks)} chunks...")
        
        # Simplificar chunks
        simplified_chunks = self.simplify_chunks(chunks, level)
        
        # Juntar chunks simplificados
        simplified_chapter = ' '.join(simplified_chunks)
        
        return simplified_chapter
    
    def _cleanup_memory(self):
        """Limpa memória GPU/RAM"""
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
    
    def get_level_description(self, level: int) -> str:
        """Retorna descrição do nível de simplificação"""
        if level in self.prompts:
            return self.prompts[level]["name"]
        return "Nível desconhecido"
    
    def get_model_info(self) -> Dict:
        """Retorna informações sobre o modelo carregado"""
        return {
            "model_name": self.model_name,
            "device": self.device,
            "model_loaded": self.model is not None,
            "tokenizer_loaded": self.tokenizer is not None,
            "pipeline_ready": self.pipeline is not None
        }

# Função utilitária para usar em outras partes do código
def create_local_simplifier(model_name="teknium/OpenHermes-2.5-Mistral-7B"):
    """Cria uma instância do simplificador local"""
    return LocalLLMSimplifier(model_name)

