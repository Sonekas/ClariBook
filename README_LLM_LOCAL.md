# Simplificador de EPUB com LLM Local

Um programa web que permite simplificar livros EPUB usando modelos de linguagem locais (open-source) em vez de APIs externas.

## 🚀 **Novidades da Versão Local**

### **Modelos Suportados**
- **Mistral-7B-Instruct-v0.3**: Modelo principal (requer GPU/CPU potente)
- **OpenHermes-2.5-Mistral-7B**: Modelo alternativo otimizado
- **Simplificador Baseado em Regras**: Fallback para ambientes limitados

### **Vantagens do LLM Local**
- ✅ **Privacidade Total**: Nenhum dado sai do seu computador
- ✅ **Sem Custos de API**: Não precisa pagar por tokens
- ✅ **Offline**: Funciona sem conexão com internet
- ✅ **Controle Total**: Customize prompts e parâmetros
- ✅ **Sem Limites**: Processe quantos livros quiser

## 📋 **Requisitos de Sistema**

### **Mínimos (Simplificador Baseado em Regras)**
- **RAM**: 4GB
- **CPU**: Qualquer processador moderno
- **Armazenamento**: 2GB livres
- **Python**: 3.11+

### **Recomendados (LLM Local)**
- **RAM**: 16GB+ (32GB ideal)
- **GPU**: NVIDIA com 8GB+ VRAM (opcional mas recomendado)
- **CPU**: 8+ cores
- **Armazenamento**: 20GB+ livres (para modelos)
- **Python**: 3.11+

### **Ideais (Performance Máxima)**
- **RAM**: 32GB+
- **GPU**: NVIDIA RTX 4090 ou similar (24GB VRAM)
- **CPU**: 16+ cores
- **Armazenamento**: SSD com 50GB+ livres

## 🛠 **Instalação**

### **1. Preparar Ambiente**
```bash
# Clonar/baixar projeto
cd simplificador-epub

# Criar ambiente virtual
python -m venv venv

# Ativar ambiente virtual
# Linux/Mac:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### **2. Instalar Dependências**
```bash
# Instalar dependências básicas
pip install -r requirements.txt

# Para GPU NVIDIA (opcional, melhora performance)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

### **3. Configurar Modelo**

O sistema tentará carregar os modelos na seguinte ordem:

1. **Mistral/OpenHermes** (se hardware suportar)
2. **Simplificador baseado em regras** (fallback)
3. **OpenAI API** (se configurada)

Para forçar uso de modelo específico, edite `src/routes/epub_processor.py`.

### **4. Executar Aplicação**
```bash
python src/main.py
```

Acesse: `http://localhost:5000`

## 🎯 **Como Usar**

### **Upload e Processamento**
1. **Envie arquivo EPUB** via interface web
2. **Escolha nível de simplificação**:
   - **Nível 1**: Muito simples (frases curtas, vocabulário básico)
   - **Nível 2**: Médio (equilibrio entre simplicidade e qualidade)
   - **Nível 3**: Comum (pequenos ajustes para fluidez)
3. **Aguarde processamento** (pode levar vários minutos)
4. **Baixe resultado** quando concluído

### **Monitoramento**
- Progresso em tempo real na interface
- Logs detalhados no terminal
- Status de cada capítulo processado

## ⚙️ **Configurações Avançadas**

### **Escolher Modelo Específico**

Edite `src/services/local_llm_simplifier.py`:

```python
# Para Mistral-7B-Instruct
simplifier = LocalLLMSimplifier("mistralai/Mistral-7B-Instruct-v0.3")

# Para OpenHermes-2.5
simplifier = LocalLLMSimplifier("teknium/OpenHermes-2.5-Mistral-7B")
```

### **Otimizar Performance**

#### **Para GPU NVIDIA**
```python
# Em local_llm_simplifier.py
model_kwargs = {
    "device_map": "auto",
    "torch_dtype": torch.float16,
    "load_in_4bit": True,  # Quantização 4-bit
}
```

#### **Para CPU Apenas**
```python
# Em local_llm_simplifier.py
model_kwargs = {
    "torch_dtype": torch.float32,
    "device_map": None,
}
```

### **Ajustar Tamanho de Chunks**
```python
# Em epub_processor.py
simplified_content = simplifier.simplify_chapter(
    chapter['content'], 
    simplification_level,
    max_chunk_words=800  # Reduzir para hardware limitado
)
```

### **Personalizar Prompts**

Edite prompts em `src/services/local_llm_simplifier.py`:

```python
self.prompts = {
    1: {
        "system": "Seu prompt personalizado aqui...",
        "user": "Reescreva este trecho..."
    }
}
```

## 🔧 **Solução de Problemas**

### **Erro: "CUDA out of memory"**
```bash
# Reduzir uso de memória GPU
export PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512

# Ou usar quantização
load_in_4bit=True
```

### **Erro: "Model too large"**
```python
# Usar modelo menor ou simplificador baseado em regras
from src.services.lightweight_llm import create_lightweight_simplifier
simplifier = create_lightweight_simplifier()
```

### **Processamento Muito Lento**
1. **Reduzir tamanho de chunks**: `max_chunk_words=500`
2. **Usar GPU**: Instalar CUDA e PyTorch GPU
3. **Usar quantização**: `load_in_4bit=True`
4. **Usar simplificador baseado em regras**

### **Erro: "Protobuf not found"**
```bash
pip install protobuf
```

### **Erro: "Bad Zip file"**
- Arquivo EPUB corrompido
- Tente com outro arquivo EPUB válido

## 📊 **Comparação de Modelos**

| Modelo | Tamanho | RAM Mín. | Qualidade | Velocidade |
|--------|---------|----------|-----------|------------|
| **Mistral-7B** | ~14GB | 16GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **OpenHermes-2.5** | ~14GB | 16GB | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Baseado em Regras** | <1MB | 4GB | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |

## 🔒 **Privacidade e Segurança**

### **Dados Locais**
- Todos os arquivos processados ficam em `/tmp/`
- Nenhum dado é enviado para servidores externos
- Modelos executam completamente offline

### **Limpeza Automática**
```python
# Arquivos temporários são limpos automaticamente
# Para limpeza manual:
rm -rf /tmp/epub_uploads/*
rm -rf /tmp/epub_processed/*
```

## 🚀 **Performance e Benchmarks**

### **Tempos Típicos (Livro de 200 páginas)**

| Hardware | Modelo | Tempo |
|----------|--------|-------|
| RTX 4090 + 32GB RAM | Mistral-7B | 5-10 min |
| RTX 3080 + 16GB RAM | OpenHermes | 10-20 min |
| CPU i7 + 16GB RAM | Baseado em Regras | 1-2 min |
| CPU i5 + 8GB RAM | Baseado em Regras | 2-5 min |

## 🔄 **Atualizações e Manutenção**

### **Atualizar Modelos**
```bash
# Limpar cache de modelos
rm -rf ~/.cache/huggingface/

# Baixar versão mais recente
python -c "from transformers import AutoTokenizer; AutoTokenizer.from_pretrained('teknium/OpenHermes-2.5-Mistral-7B')"
```

### **Monitorar Uso de Recursos**
```bash
# Monitorar GPU
nvidia-smi

# Monitorar RAM
htop

# Monitorar disco
df -h
```

## 📚 **Recursos Adicionais**

### **Links Úteis**
- [Mistral-7B-Instruct](https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3)
- [OpenHermes-2.5-Mistral-7B](https://huggingface.co/teknium/OpenHermes-2.5-Mistral-7B)
- [Documentação Transformers](https://huggingface.co/docs/transformers)
- [PyTorch GPU Setup](https://pytorch.org/get-started/locally/)

### **Comunidade**
- Issues e sugestões: GitHub Issues
- Discussões: GitHub Discussions
- Contribuições: Pull Requests bem-vindos

## 📄 **Licença**

Este projeto é fornecido como está, para fins educacionais e de demonstração.

---

**🎉 Aproveite a liberdade de processar seus livros localmente, com privacidade total e sem custos!**

