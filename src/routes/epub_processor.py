import os
import logging
import tempfile
import zipfile
from flask import Blueprint, request, jsonify, send_file
from werkzeug.utils import secure_filename
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import traceback
from flask_cors import cross_origin
from src.services.hf_simplifier import rewrite_with_context, summarize_text, improve_transitions

logger = logging.getLogger(__name__)
epub_bp = Blueprint('epub', __name__)

# Diretório para armazenar arquivos temporários
BASE_TMP_DIR = os.path.join(tempfile.gettempdir(), 'epub_simplifier')
UPLOAD_FOLDER = os.path.join(BASE_TMP_DIR, 'epub_uploads')
PROCESSED_FOLDER = os.path.join(BASE_TMP_DIR, 'epub_processed')
STATUS_FOLDER = os.path.join(BASE_TMP_DIR, 'epub_status')

# Criar diretórios se não existirem
os.makedirs(BASE_TMP_DIR, exist_ok=True)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)
os.makedirs(STATUS_FOLDER, exist_ok=True)

# Dicionário para armazenar status de processamento
processing_status = {}

def extract_text_from_epub(epub_path):
    """Extrai texto de um arquivo EPUB e retorna uma lista de capítulos"""
    book = epub.read_epub(epub_path)
    chapters = []
    
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
# Extrair texto HTML
            content = item.get_content().decode('utf-8')
            
            # Usar BeautifulSoup para extrair texto limpo
            soup = BeautifulSoup(content, 'html.parser')
            text = soup.get_text()
            
            # Limpar texto (remover espaços extras, quebras de linha desnecessárias)
            text = re.sub(r'\n\s*\n', '\n\n', text)
            text = re.sub(r' +', ' ', text)
            text = text.strip()
            
            # Incluir todos os documentos, mesmo com pouco texto (preserva capítulos/imagens)
            chapters.append({
                'id': item.get_id(),
                'title': item.get_name(),
                'content': text
            })
    
    return chapters

def split_text_into_chunks(text, max_words=1500):
    """Divide texto em chunks menores para processamento"""
    words = text.split()
    # Tratar páginas com texto mínimo (ex.: capa, páginas só com imagens)
    if len(words) < 5:
        return []
    chunks = []
    
    for i in range(0, len(words), max_words):
        chunk = ' '.join(words[i:i + max_words])
        chunks.append(chunk)
    
    return chunks

def create_epub_from_chapters(chapters, original_epub_path, output_path, title_suffix=""):
    """Cria um novo EPUB a partir dos capítulos processados"""
    # Ler o EPUB original para manter metadados
    original_book = epub.read_epub(original_epub_path)
    
    # Criar novo livro
    book = epub.EpubBook()
    
    # Copiar metadados básicos
    book.set_identifier(str(uuid.uuid4()))
    # Título seguro mesmo quando metadados estão ausentes
    try:
        title_meta = original_book.get_metadata('DC', 'title')
        title_val = title_meta[0][0] if title_meta and title_meta[0] and title_meta[0][0] else ''
    except Exception:
        title_val = ''
    book.set_title((title_val or 'EPUB') + title_suffix)
    book.set_language('pt')
    
    # Adicionar autor se existir (com checagens seguras)
    try:
        authors = original_book.get_metadata('DC', 'creator')
        if authors and authors[0] and authors[0][0]:
            book.add_author(authors[0][0])
    except Exception:
        pass
    
    # Criar capítulos
    epub_chapters = []
    toc = []
    
    for i, chapter in enumerate(chapters):
        # Criar capítulo EPUB
        c = epub.EpubHtml(
            title=f'Capítulo {i+1}',
            file_name=f'chap_{i+1}.xhtml',
            lang='pt'
        )
        
        # Adicionar conteúdo HTML
        content_html = chapter['content'].replace('\n\n', '</p><p>').replace('\n', '<br/>')
        c.content = f'''
        <html xmlns="http://www.w3.org/1999/xhtml">
        <head>
            <title>Capítulo {i+1}</title>
        </head>
        <body>
            <h1>Capítulo {i+1}</h1>
            <p>{content_html}</p>
        </body>
        </html>
        '''
        
        book.add_item(c)
        epub_chapters.append(c)
        toc.append(c)
    
    # Adicionar CSS básico
    style = '''
    body { font-family: Arial, sans-serif; margin: 2em; }
    h1 { color: #333; }
    p { text-align: justify; line-height: 1.6; }
    '''
    nav_css = epub.EpubItem(
        uid="nav_css",
        file_name="style/nav.css",
        media_type="text/css",
        content=style
    )
    book.add_item(nav_css)
    
    # Configurar navegação
    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    
    # Definir ordem de leitura
    book.spine = ['nav'] + epub_chapters if epub_chapters else ['nav']
    
    # Salvar EPUB
    epub.write_epub(output_path, book, {})
    
    return output_path

def write_simplified_epub_preserving_structure(chapters, original_epub_path, output_path, title_suffix=""):
    """Escreve um EPUB mantendo estrutura original (TOC, spine, CSS, imagens),
    substituindo apenas o texto dos documentos por versões simplificadas,
    preservando posição das imagens e espaçamento/estrutura original.
    """
    # Mapa id -> conteúdo simplificado
    simplified_by_id = {c.get('id'): c.get('content', '') for c in chapters}

    book = epub.read_epub(original_epub_path)

    # Atualizar título com sufixo, mantendo metadados originais
    try:
        orig_title_meta = book.get_metadata('DC', 'title')
        title_val = orig_title_meta[0][0] if orig_title_meta and orig_title_meta[0] and orig_title_meta[0][0] else ''
        if title_val:
            book.set_title(f"{title_val}{title_suffix}")
        else:
            # Mantém título existente sem indexing, se disponível
            pass
    except Exception:
        pass

    # Percorrer documentos e substituir conteúdo textual sem alterar imagens ou ordem
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            try:
                html = item.get_content().decode('utf-8', errors='ignore')
                soup = BeautifulSoup(html, 'html.parser')
                body = soup.find('body') or soup

                # Heading original (h1/h2/h3) é mantido
                heading_tag = soup.find(['h1', 'h2', 'h3'])
                original_heading = heading_tag.get_text(strip=True) if heading_tag else None

                # Texto simplificado para este documento
                simplified_text = simplified_by_id.get(item.get_id())
                if simplified_text is None or not str(simplified_text).strip():
                    # Nada a substituir; mantém documento como está (capa/imagens/folha de rosto)
                    item.set_content(str(soup).encode('utf-8'))
                    continue

                # Quebrar texto simplificado em parágrafos preservando espaçamento por \n\n
                simplified_paragraphs = [p.strip() for p in simplified_text.split('\n\n') if p.strip()]
                if not simplified_paragraphs and str(simplified_text).strip():
                    simplified_paragraphs = [str(simplified_text).strip()]

                # Substituir conteúdo textual dos parágrafos existentes na ordem, sem remover imagens
                paras = body.find_all('p')
                sp_idx = 0
                for p in paras:
                    if sp_idx < len(simplified_paragraphs):
                        # Limpa o conteúdo do parágrafo e insere o texto simplificado correspondente
                        p.clear()
                        p.append(simplified_paragraphs[sp_idx])
                        sp_idx += 1
                    else:
                        # Se acabaram os parágrafos simplificados, mantém espaçamento com parágrafos vazios
                        p.clear()
                        p.append('')

                # Se existem mais parágrafos simplificados do que <p> originais, adiciona ao final
                while sp_idx < len(simplified_paragraphs):
                    new_p = soup.new_tag('p')
                    new_p.string = simplified_paragraphs[sp_idx]
                    body.append(new_p)
                    sp_idx += 1

                # Mantém o heading original (não altera)
                # Mantém imagens e demais elementos na posição original (não removemos/extraímos nada)

                # Gravar conteúdo atualizado
                item.set_content(str(soup).encode('utf-8'))
            except Exception:
                # Em caso de falha, deixa o item original intacto
                pass

    # Salvar EPUB preservando estrutura original e capa/imagens
    epub.write_epub(output_path, book, {})
    return output_path

@epub_bp.route('/upload', methods=['POST'])
@cross_origin()
def upload_epub():
    """Endpoint para upload de arquivo EPUB"""
    logger.info("Upload recebido")
    if 'file' not in request.files:
        logger.warning("Upload sem arquivo no formulário")
        return jsonify({'error': 'Nenhum arquivo enviado'}), 400
    
    file = request.files['file']
    if file.filename == '':
        logger.warning("Upload com filename vazio")
        return jsonify({'error': 'Nenhum arquivo selecionado'}), 400
    
    if not file.filename.lower().endswith('.epub'):
        logger.warning("Upload com extensão inválida: %s", file.filename)
        return jsonify({'error': 'Arquivo deve ser um EPUB'}), 400
    
    filename = secure_filename(file.filename)
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_FOLDER, f"{file_id}_{filename}")
    
    try:
        file.save(file_path)
        chapters = extract_text_from_epub(file_path)
        
        # Salvar informações do arquivo para processamento posterior
        file_info = {
            'file_id': file_id,
            'original_filename': filename,
            'file_path': file_path,
            'chapters_count': len(chapters),
            'total_words': sum(len(chapter['content'].split()) for chapter in chapters)
        }
        
        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': filename,
            'chapters_count': len(chapters),
            'total_words': file_info['total_words'],
            'message': 'Arquivo carregado com sucesso'
        })
        
    except Exception as e:
        logger.exception("Erro ao processar upload: %s", str(e))
        return jsonify({'error': f'Erro ao processar EPUB: {str(e)}'}), 500

def _split_words_with_overlap(text: str, chunk_size: int = 350, overlap: int = 50):
    words = text.split()
    if len(words) < 5:
        return []
    chunks = []
    start = 0
    while start < len(words):
        end = min(len(words), start + chunk_size)
        chunk_words = words[start:end]
        chunks.append(" ".join(chunk_words))
        if end >= len(words):
            break
        start = max(0, end - overlap)
    return chunks


def _last_tail(text: str, max_chars: int = 400) -> str:
    s = (text or "").strip()
    return s[-max_chars:] if len(s) > max_chars else s


def _level_name(level: int) -> str:
    if level == 1:
        return "leve"
    if level == 2:
        return "moderado"
    return "agressivo"


def process_epub_with_ai(file_id, original_path, simplification_level):
    """Processa EPUB com Hugging Face Inference API, usando contexto global e por capítulo."""
    try:
        logger.info("Processamento (HF) iniciado file_id=%s nivel=%s", file_id, simplification_level)
        processing_status[file_id] = {
            'status': 'processing',
            'progress': 0,
            'message': 'Lendo capítulos...',
            'total_chapters': 0,
            'processed_chapters': 0
        }

        chapters = extract_text_from_epub(original_path)
        total_chapters = len(chapters)
        processing_status[file_id].update({'total_chapters': total_chapters})

        fast_mode = os.getenv("FAST_MODE", "0") == "1"
        max_workers = int(os.getenv("MAX_WORKERS", "2"))
        cp_dir = _get_checkpoint_dir(file_id)
        _ensure_dir(cp_dir)
        global_meta_path = os.path.join(cp_dir, 'meta.json')
        global_meta = _load_json(global_meta_path) or {}
        global_meta.update({
            'simplification_level': simplification_level,
            'total_chapters': total_chapters
        })
        sample_texts = []
        for ch in chapters[:8]:
            t = (ch.get('content') or "").strip()
            if t:
                sample_texts.append(t[:2000])
        global_text = "\n\n".join(sample_texts)[:15000]
        global_summary = "" if fast_mode else (summarize_text(global_text, scope="geral") if global_text else "")
        if fast_mode:
            global_summary = ""
        else:
            cached_global = global_meta.get('global_summary')
            if cached_global:
                global_summary = cached_global
            else:
                global_summary = summarize_text(global_text, scope="geral") if global_text else ""
                global_meta['global_summary'] = global_summary
        _save_json(global_meta_path, global_meta)
        processed_chapters = []
        level_str = _level_name(int(simplification_level))
        processed_chapters = [None] * total_chapters

        def _process_chapter(i: int, chapter: dict):
            processing_status[file_id].update({
                'processed_chapters': i,
                'progress': int((i / total_chapters) * 100) if total_chapters else 0,
                'message': f'Preparando capítulo {i+1}/{total_chapters}...'
            })

            chapter_text = chapter.get('content') or ""
            if len(chapter_text.split()) < 5:
                return i, {
                    'id': chapter['id'],
                    'title': chapter['title'],
                    'content': chapter_text
                }

            chapter_meta_path = os.path.join(cp_dir, f'chapter_{i}_meta.json')
            chapter_chunks_path = os.path.join(cp_dir, f'chapter_{i}_chunks.json')
            chapter_meta = _load_json(chapter_meta_path) or {}

            if chapter_meta.get('complete'):
                saved_chunks = _load_json(chapter_chunks_path) or []
                if saved_chunks:
                    chapter_rewritten = "\n\n".join(saved_chunks)
                    chapter_final = chapter_rewritten if fast_mode else improve_transitions(chapter_rewritten)
                    return i, {
                        'id': chapter['id'],
                        'title': chapter['title'],
                        'content': chapter_final
                    }

            if fast_mode:
                chapter_summary = ""
            else:
                cached_summary = chapter_meta.get('chapter_summary')
                if cached_summary:
                    chapter_summary = cached_summary
                else:
                    chapter_summary = summarize_text(chapter_text[:15000], scope="capítulo")
                    chapter_meta['chapter_summary'] = chapter_summary
                    _save_json(chapter_meta_path, chapter_meta)

            chunk_size = 600 if fast_mode else 350
            overlap = 20 if fast_mode else 50
            chunks = _split_words_with_overlap(chapter_text, chunk_size=chunk_size, overlap=overlap)

            existing_chunks = _load_json(chapter_chunks_path) or []
            processed_count = int(chapter_meta.get('processed_chunks', len(existing_chunks)))
            processed_count = max(0, min(processed_count, len(chunks)))
            rewritten_parts = list(existing_chunks)
            prev_tail = _last_tail(rewritten_parts[-1], 400) if rewritten_parts else ""

            for j in range(processed_count, len(chunks)):
                chunk = chunks[j]
                try:
                    rewritten = rewrite_with_context(
                        text_block=chunk,
                        global_summary=global_summary,
                        chapter_summary=chapter_summary,
                        previous_output_tail=prev_tail,
                        level=level_str,
                    )
                except Exception:
                    rewritten = chunk
                rewritten_parts.append(rewritten)
                prev_tail = _last_tail(rewritten, 400)
                _save_json(chapter_chunks_path, rewritten_parts)
                chapter_meta.update({'processed_chunks': j + 1, 'total_chunks': len(chunks), 'complete': False})
                _save_json(chapter_meta_path, chapter_meta)

                processing_status[file_id].update({
                    'processed_chapters': i,
                    'progress': int(((i + ((j + 1) / max(1, len(chunks)))) / total_chapters) * 100) if total_chapters else 100,
                    'message': f'Cap. {i+1}/{total_chapters}: reescrevendo parte {j+1}/{len(chunks)}'
                })

            chapter_rewritten = "\n\n".join(rewritten_parts)
            chapter_final = chapter_rewritten if fast_mode else improve_transitions(chapter_rewritten)
            chapter_meta.update({'processed_chunks': len(chunks), 'total_chunks': len(chunks), 'complete': True})
            _save_json(chapter_meta_path, chapter_meta)
            _save_json(chapter_chunks_path, rewritten_parts)

            return i, {
                'id': chapter['id'],
                'title': chapter['title'],
                'content': chapter_final
            }

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_process_chapter, i, chapter) for i, chapter in enumerate(chapters)]
            completed = 0
            for future in as_completed(futures):
                idx, chapter_out = future.result()
                processed_chapters[idx] = chapter_out
                completed += 1
                processing_status[file_id].update({
                    'processed_chapters': completed,
                    'progress': int((completed / total_chapters) * 100) if total_chapters else 100,
                    'message': f'Capítulos finalizados: {completed}/{total_chapters}'
                })
        output_filename = f"{file_id}_simplified_level_{simplification_level}.epub"
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)
        output_path = os.path.join(PROCESSED_FOLDER, output_filename)

        processing_status[file_id].update({
            'message': 'Gerando EPUB final...',
            'progress': 95
        })

        level_names = {1: " - Muito Simples", 2: " - Médio", 3: " - Comum"}
        write_simplified_epub_preserving_structure(
            processed_chapters,
            original_path,
            output_path,
            level_names.get(simplification_level, "")
        )

        processing_status[file_id] = {
            'status': 'completed',
            'progress': 100,
            'message': 'Processamento concluído!',
            'output_file': output_filename,
            'total_chapters': total_chapters,
            'processed_chapters': total_chapters
        }

    except Exception as e:
        logger.exception("Erro no processamento (HF) file_id=%s", file_id)
        processing_status[file_id] = {
            'status': 'error',
            'progress': 0,
            'message': f'Erro: {str(e)}',
            'error': str(e),
            'exception': traceback.format_exc()
        }

@epub_bp.route('/process', methods=['POST'])
@cross_origin()
def process_epub():
    """Endpoint para processar EPUB com simplificação"""
    data = request.get_json()
    logger.info("Processar solicitado")
    
    if not data or 'file_id' not in data or 'simplification_level' not in data:
        logger.warning("Processar com dados inválidos: %s", data)
        return jsonify({'error': 'Dados inválidos'}), 400
    
    file_id = data['file_id']
    simplification_level = data['simplification_level']
    
    if simplification_level not in [1, 2, 3]:
        logger.warning("Nível inválido: %s", simplification_level)
        return jsonify({'error': 'Nível de simplificação deve ser 1, 2 ou 3'}), 400
    
    # Encontrar arquivo original
    original_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(file_id)]
    if not original_files:
        logger.warning("Arquivo não encontrado para file_id=%s", file_id)
        return jsonify({'error': 'Arquivo não encontrado'}), 404
    
    original_path = os.path.join(UPLOAD_FOLDER, original_files[0])
    
    # Verificar se já está sendo processado
    if file_id in processing_status and processing_status[file_id]['status'] == 'processing':
        logger.warning("Arquivo já em processamento file_id=%s", file_id)
        return jsonify({'error': 'Arquivo já está sendo processado'}), 400
    
    # Iniciar processamento em thread separada
    thread = threading.Thread(
        target=process_epub_with_ai,
        args=(file_id, original_path, simplification_level)
    )
    thread.daemon = True
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Processamento iniciado',
        'file_id': file_id
    })

@epub_bp.route('/download/<file_id>')
@cross_origin()
def download_processed(file_id):
    """Endpoint para download do arquivo processado"""
    file_path = os.path.join(PROCESSED_FOLDER, file_id)
    
    if not os.path.exists(file_path):
        logger.warning("Download não encontrado file_id=%s", file_id)
        return jsonify({'error': 'Arquivo não encontrado'}), 404
    
    return send_file(file_path, as_attachment=True, download_name=file_id)

@epub_bp.route('/status/<file_id>')
@cross_origin()
def get_status(file_id):
    """Endpoint para verificar status do processamento"""
    # Verificar se arquivo original existe
    original_files = [f for f in os.listdir(UPLOAD_FOLDER) if f.startswith(file_id)]
    if not original_files:
        logger.warning("Status com arquivo inexistente file_id=%s", file_id)
        return jsonify({'error': 'Arquivo não encontrado'}), 404
    
    # Verificar status de processamento
    if file_id in processing_status:
        status_info = processing_status[file_id].copy()
        status_info['file_id'] = file_id
        return jsonify(status_info)
    
    # Verificar arquivos processados
    processed_files = [f for f in os.listdir(PROCESSED_FOLDER) if f.startswith(file_id)]
    
    return jsonify({
        'file_id': file_id,
        'status': 'ready',
        'original_exists': len(original_files) > 0,
        'processed_files': processed_files,
        'message': 'Arquivo pronto para processamento'
    })


# Utilitários de checkpoint/resumo
import hashlib


def _get_checkpoint_dir(file_id: str) -> str:
    return os.path.join(STATUS_FOLDER, 'checkpoints', file_id)


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _load_json(path: str):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        return None
    return None


def _save_json(path: str, data: dict):
    try:
        _ensure_dir(os.path.dirname(path))
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def _hash_chunk(text: str, level: int) -> str:
    h = hashlib.sha256()
    h.update(f"{level}|".encode('utf-8'))
    h.update(text.encode('utf-8'))
    return h.hexdigest()

