# Simplificador de EPUB

Um programa web simples que permite aos usuários enviar arquivos EPUB, escolher entre 3 níveis de simplificação de texto, e baixar ou visualizar o livro convertido usando IA para reescrita.

## Funcionalidades

### Principais Recursos
- **Upload de EPUB**: Interface drag-and-drop para envio de arquivos EPUB
- **3 Níveis de Simplificação**:
  1. **Muito Simples**: Frases curtas e vocabulário acessível
  2. **Médio**: Linguagem clara mantendo parte da riqueza literária
  3. **Comum**: Pequenas simplificações para melhorar fluidez
- **Processamento com IA**: Utiliza Hugging Face Inference API para reescrita
- **Interface Moderna**: Design responsivo e intuitivo
- **Monitoramento de Progresso**: Acompanhamento em tempo real do processamento
- **Download Direto**: Baixe o EPUB simplificado diretamente

### Tecnologias Utilizadas

#### Backend
- **Flask**: Framework web Python
- **ebooklib**: Biblioteca para manipulação de arquivos EPUB
- **Hugging Face Inference API**: Reescrita do texto
- **BeautifulSoup4**: Parsing de conteúdo HTML
- **Flask-CORS**: Suporte a requisições cross-origin

#### Frontend
- **HTML5/CSS3/JavaScript**: Interface web moderna
- **Font Awesome**: Ícones
- **Design Responsivo**: Compatível com desktop e mobile

## Instalação e Configuração

### Pré-requisitos
- Python 3.11+
- Token da Hugging Face (HF_TOKEN)

### Passos de Instalação

1. **Clone ou baixe o projeto**
   ```bash
   # Se usando git
   git clone <repository-url>
   cd epub-simplifier
   ```

2. **Crie e ative o ambiente virtual**
   ```bash
   python -m venv venv
   
   # No Linux/Mac
   source venv/bin/activate
   
   # No Windows
   venv\Scripts\activate
   ```

3. **Instale as dependências**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure o token da Hugging Face**
   ```bash
   # Linux/Mac
   export HF_TOKEN="seu-token-aqui"
   
   # Windows
   set HF_TOKEN=seu-token-aqui
   ```

5. **Execute a aplicação**
   ```bash
   python src/main.py
   ```

6. **Acesse no navegador**
   ```
   http://localhost:5000
   ```

## Como Usar

### Passo a Passo

1. **Envie seu arquivo EPUB**
   - Clique em "Escolher Arquivo" ou arraste e solte um arquivo EPUB
   - Aguarde o upload e análise do arquivo

2. **Escolha o nível de simplificação**
   - **Nível 1 - Muito Simples**: Para iniciantes ou leitores com dificuldades
   - **Nível 2 - Médio**: Equilibrio entre simplicidade e qualidade (recomendado)
   - **Nível 3 - Comum**: Mantém quase toda a riqueza original

3. **Inicie o processamento**
   - Clique em "Iniciar Simplificação"
   - Acompanhe o progresso em tempo real

4. **Baixe o resultado**
   - Quando concluído, clique em "Baixar EPUB Simplificado"
   - O arquivo será baixado automaticamente

### Dicas de Uso

- **Arquivos grandes**: O processamento pode levar vários minutos dependendo do tamanho do livro
- **Qualidade da IA**: O nível 2 (Médio) oferece o melhor equilibrio entre simplicidade e qualidade
- **Formatos suportados**: Apenas arquivos .epub são aceitos
- **Limitações**: Funciona melhor com textos em português

## Estrutura do Projeto

```
epub-simplifier/
├── src/
│   ├── main.py                 # Arquivo principal do Flask
│   ├── routes/
│   │   └── epub_processor.py   # Rotas de processamento EPUB
│   ├── services/
│   │   └── hf_simplifier.py   # Serviço de simplificação via Hugging Face
│   ├── static/
│   │   ├── index.html         # Interface principal
│   │   ├── styles.css         # Estilos CSS
│   │   └── script.js          # JavaScript frontend
├── venv/                      # Ambiente virtual Python
├── requirements.txt           # Dependências Python
└── README.md                 # Esta documentação
```

## API Endpoints

### Upload de EPUB
```
POST /api/epub/upload
Content-Type: multipart/form-data

Parâmetros:
- file: arquivo EPUB

Resposta:
{
  "success": true,
  "file_id": "uuid-do-arquivo",
  "filename": "nome-do-arquivo.epub",
  "chapters_count": 15,
  "total_words": 45000
}
```

### Processar EPUB
```
POST /api/epub/process
Content-Type: application/json

Body:
{
  "file_id": "uuid-do-arquivo",
  "simplification_level": 2
}

Resposta:
{
  "success": true,
  "message": "Processamento iniciado",
  "file_id": "uuid-do-arquivo"
}
```

### Status do Processamento
```
GET /api/epub/status/{file_id}

Resposta:
{
  "file_id": "uuid-do-arquivo",
  "status": "processing",
  "progress": 45,
  "message": "Processando capítulo 3 de 15...",
  "total_chapters": 15,
  "processed_chapters": 3
}
```

### Download do Resultado
```
GET /api/epub/download/{output_filename}

Resposta: Arquivo EPUB simplificado
```

## Solução de Problemas

### Erros Comuns

1. **"Bad Zip file"**
   - O arquivo EPUB está corrompido ou não é um EPUB válido
   - Tente com outro arquivo EPUB

2. **"Erro de conexão durante o processamento"**
   - Verifique sua conexão com a internet
   - Confirme se a variável `HF_TOKEN` está configurada corretamente

3. **Processamento muito lento**
   - Arquivos grandes podem levar tempo
   - Considere usar um modelo mais rápido ou reduzir o tamanho dos chunks

### Logs e Debugging

Para ativar logs detalhados, adicione ao início do `main.py`:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Limitações Conhecidas

- **Tamanho de arquivo**: Arquivos muito grandes podem causar timeout
- **Idioma**: Otimizado para textos em português
- **Custo da API**: Uso intensivo pode gerar custos dependendo do provedor
- **Formatação**: Algumas formatações complexas podem ser perdidas

## Contribuição

Para contribuir com o projeto:

1. Faça um fork do repositório
2. Crie uma branch para sua feature
3. Implemente suas mudanças
4. Teste thoroughly
5. Submeta um pull request

## Licença

Este projeto é fornecido como está, para fins educacionais e de demonstração.

## Suporte

Para dúvidas ou problemas:
- Verifique a seção de solução de problemas
- Consulte os logs da aplicação
- Teste com arquivos EPUB menores primeiro

---

**Desenvolvido com Flask e muito ☕**
