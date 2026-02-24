// Variáveis globais
let currentFileId = null;
let processingInterval = null;

// Elementos DOM
const uploadSection = document.getElementById('uploadSection');
const configSection = document.getElementById('configSection');
const progressSection = document.getElementById('progressSection');
const resultSection = document.getElementById('resultSection');
const errorSection = document.getElementById('errorSection');

const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');
const fileInfo = document.getElementById('fileInfo');
const fileName = document.getElementById('fileName');
const fileStats = document.getElementById('fileStats');

const progressFill = document.getElementById('progressFill');
const progressMessage = document.getElementById('progressMessage');
const progressStats = document.getElementById('progressStats');

const downloadBtn = document.getElementById('downloadBtn');
const errorMessage = document.getElementById('errorMessage');

const API_BASE = window.location.port === '5000'
    ? window.location.origin
    : (window.location.hostname ? `http://${window.location.hostname}:5000` : 'http://127.0.0.1:5000');

async function readResponseData(response) {
    const contentType = response.headers.get('content-type') || '';
    const statusInfo = `HTTP ${response.status}${response.statusText ? ` - ${response.statusText}` : ''}`;
    if (contentType.includes('application/json')) {
        const data = await response.json();
        if (!response.ok) {
            return { error: `${data.error || 'Erro na requisição'} (${statusInfo})` };
        }
        return data;
    }
    const text = await response.text();
    if (!response.ok) {
        return { error: `${text || 'Erro na requisição'} (${statusInfo})` };
    }
    return { message: text };
}

// Event listeners
document.addEventListener('DOMContentLoaded', function() {
    setupEventListeners();
});

function setupEventListeners() {
    // Upload de arquivo
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);
    uploadArea.addEventListener('click', () => fileInput.click());
    
    // Seleção de nível
    const levelOptions = document.querySelectorAll('.level-option');
    levelOptions.forEach(option => {
        option.addEventListener('click', function() {
            const radio = this.querySelector('input[type="radio"]');
            radio.checked = true;
            updateLevelSelection();
        });
    });
    
    // Radio buttons
    const radioButtons = document.querySelectorAll('input[name="level"]');
    radioButtons.forEach(radio => {
        radio.addEventListener('change', updateLevelSelection);
    });
}

// Funções de drag and drop
function handleDragOver(e) {
    e.preventDefault();
    uploadArea.classList.add('dragover');
}

function handleDragLeave(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
}

function handleDrop(e) {
    e.preventDefault();
    uploadArea.classList.remove('dragover');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        const file = files[0];
        if (file.name.toLowerCase().endsWith('.epub')) {
            fileInput.files = files;
            handleFileSelect();
        } else {
            showError('Por favor, selecione um arquivo EPUB válido.');
        }
    }
}

// Manipulação de arquivo
function handleFileSelect() {
    const file = fileInput.files[0];
    if (!file) return;
    
    if (!file.name.toLowerCase().endsWith('.epub')) {
        showError('Por favor, selecione um arquivo EPUB válido.');
        return;
    }
    
    // Mostrar informações do arquivo
    fileName.textContent = file.name;
    fileStats.textContent = `Tamanho: ${formatFileSize(file.size)}`;
    
    // Esconder área de upload e mostrar info do arquivo
    uploadArea.style.display = 'none';
    fileInfo.style.display = 'flex';
    
    // Upload do arquivo
    uploadFile(file);
}

function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

function removeFile() {
    fileInput.value = '';
    uploadArea.style.display = 'block';
    fileInfo.style.display = 'none';
    configSection.style.display = 'none';
    currentFileId = null;
}

// Upload do arquivo
async function uploadFile(file) {
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${API_BASE}/api/epub/upload`, {
            method: 'POST',
            body: formData
        });
        
        const data = await readResponseData(response);
        
        if (data.success) {
            currentFileId = data.file_id;
            
            // Atualizar estatísticas do arquivo
            fileStats.textContent = `Tamanho: ${formatFileSize(file.size)} | Capítulos: ${data.chapters_count} | Palavras: ${data.total_words.toLocaleString()}`;
            
            // Mostrar seção de configuração
            configSection.style.display = 'block';
            
            // Scroll suave para a seção de configuração
            configSection.scrollIntoView({ behavior: 'smooth' });
        } else {
            showError(data.error || 'Erro ao fazer upload do arquivo');
        }
    } catch (error) {
        console.error('Erro no upload:', { error, url: `${API_BASE}/api/epub/upload` });
        showError(`Erro de conexão: ${error.message || 'Falha de rede'}`);
    }
}

// Seleção de nível
function updateLevelSelection() {
    const levelOptions = document.querySelectorAll('.level-option');
    const selectedRadio = document.querySelector('input[name="level"]:checked');
    
    levelOptions.forEach(option => {
        option.classList.remove('selected');
    });
    
    if (selectedRadio) {
        const selectedOption = selectedRadio.closest('.level-option');
        selectedOption.classList.add('selected');
    }
}

// Iniciar processamento
async function startProcessing() {
    if (!currentFileId) {
        showError('Nenhum arquivo selecionado');
        return;
    }
    
    const selectedLevel = document.querySelector('input[name="level"]:checked');
    if (!selectedLevel) {
        showError('Selecione um nível de simplificação');
        return;
    }
    
    const level = parseInt(selectedLevel.value);
    
    try {
        // Esconder seções anteriores e mostrar progresso
        hideAllSections();
        progressSection.style.display = 'block';
        progressSection.scrollIntoView({ behavior: 'smooth' });
        
        // Iniciar processamento
        const response = await fetch(`${API_BASE}/api/epub/process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_id: currentFileId,
                simplification_level: level
            })
        });
        
        const data = await readResponseData(response);
        
        if (data.success) {
            // Iniciar monitoramento do progresso
            startProgressMonitoring();
        } else {
            showError(data.error || 'Erro ao iniciar processamento');
        }
    } catch (error) {
        console.error('Erro no processamento:', { error, url: `${API_BASE}/api/epub/process` });
        showError(`Erro de conexão: ${error.message || 'Falha de rede'}`);
    }
}

// Monitoramento do progresso
function startProgressMonitoring() {
    processingInterval = setInterval(async () => {
        try {
            const response = await fetch(`${API_BASE}/api/epub/status/${currentFileId}`);
            const data = await readResponseData(response);
            
            if (data.error) {
                clearInterval(processingInterval);
                showError(data.error);
                return;
            }
            
            // Atualizar interface de progresso
            updateProgress(data);
            
            // Verificar se terminou
            if (data.status === 'completed') {
                clearInterval(processingInterval);
                showResult(data);
            } else if (data.status === 'error') {
                clearInterval(processingInterval);
                showError(data.message || 'Erro no processamento');
            }
        } catch (error) {
            console.error('Erro ao verificar status:', { error, url: `${API_BASE}/api/epub/status/${currentFileId}` });
            clearInterval(processingInterval);
            showError(`Erro de conexão durante o processamento: ${error.message || 'Falha de rede'}`);
        }
    }, 2000); // Verificar a cada 2 segundos
}

function updateProgress(data) {
    const progress = data.progress || 0;
    progressFill.style.width = progress + '%';
    progressMessage.textContent = data.message || 'Processando...';
    
    if (data.total_chapters && data.processed_chapters !== undefined) {
        progressStats.textContent = `Capítulos processados: ${data.processed_chapters} de ${data.total_chapters}`;
    }
}

// Mostrar resultado
function showResult(data) {
    hideAllSections();
    resultSection.style.display = 'block';
    resultSection.scrollIntoView({ behavior: 'smooth' });
    
    // Configurar botão de download
    downloadBtn.onclick = () => {
        window.open(`${API_BASE}/api/epub/download/${data.output_file}`, '_blank');
    };
}

// Mostrar erro
function showError(message) {
    hideAllSections();
    errorSection.style.display = 'block';
    errorMessage.textContent = message;
    errorSection.scrollIntoView({ behavior: 'smooth' });
    
    // Limpar interval se estiver rodando
    if (processingInterval) {
        clearInterval(processingInterval);
        processingInterval = null;
    }
}

// Esconder todas as seções
function hideAllSections() {
    configSection.style.display = 'none';
    progressSection.style.display = 'none';
    resultSection.style.display = 'none';
    errorSection.style.display = 'none';
}

// Reset da aplicação
function resetApp() {
    // Limpar interval
    if (processingInterval) {
        clearInterval(processingInterval);
        processingInterval = null;
    }
    
    // Reset variáveis
    currentFileId = null;
    
    // Reset interface
    fileInput.value = '';
    uploadArea.style.display = 'block';
    fileInfo.style.display = 'none';
    hideAllSections();
    
    // Mostrar seção de upload
    uploadSection.style.display = 'block';
    uploadSection.scrollIntoView({ behavior: 'smooth' });
    
    // Reset seleção de nível
    const defaultLevel = document.getElementById('level2');
    if (defaultLevel) {
        defaultLevel.checked = true;
        updateLevelSelection();
    }
}

// Inicializar seleção de nível ao carregar
document.addEventListener('DOMContentLoaded', function() {
    updateLevelSelection();
});
