# 🔮 Oráculo - Análise Inteligente de Documentos do SharePoint

O Oráculo é uma ferramenta que permite acessar documentos visuais do SharePoint, extrair texto via OCR e responder perguntas usando IA, eliminando a necessidade de navegação manual entre bibliotecas.

## 📋 Funcionalidades

- **Integração com SharePoint**: Acessa bibliotecas e baixa documentos visuais
- **OCR Avançado**: Extrai texto de imagens e PDFs
- **IA para Análise**: Responde perguntas baseadas no conteúdo extraído
- **Interface Intuitiva**: Fácil de usar e acessível via navegador

## 🛠️ Requisitos

- Python 3.8+
- Tesseract OCR instalado no sistema (para OCR local)
- Poppler instalado (para processamento de PDFs)
- Credenciais do Microsoft Graph API
- Chave de API da OpenAI

## ⚙️ Instalação

### 1. Instalar o Tesseract OCR

**Para Windows:**
- Baixe o instalador em: https://github.com/UB-Mannheim/tesseract/wiki
- Instale e adicione ao PATH do sistema

**Para macOS:**
```bash
brew install tesseract
```

**Para Linux:**
```bash
sudo apt update
sudo apt install tesseract-ocr
sudo apt install tesseract-ocr-por  # Para suporte ao português
```

### 2. Instalar o Poppler (para processamento de PDFs)

**Para Windows:**
- Baixe de: https://github.com/oschwartz10612/poppler-windows/releases/
- Extraia e adicione a pasta `bin` ao PATH

**Para macOS:**
```bash
brew install poppler
```

**Para Linux:**
```bash
sudo apt install poppler-utils
```

### 3. Configurar o ambiente Python

```bash
# Clonar o repositório
git clone https://github.com/seu-usuario/oraculo.git
cd oraculo

# Criar e ativar ambiente virtual
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
```

### 4. Configurar as credenciais

Crie um arquivo `.streamlit/secrets.toml` com as seguintes informações:

```toml
CLIENT_ID = "seu_client_id"
CLIENT_SECRET = "seu_client_secret"
TENANT_ID = "seu_tenant_id"
OPENAI_API_KEY = "sua_chave_openai"
```

## 🚀 Executando localmente

```bash
streamlit run streamlit_app.py
```

## 📊 Uso no Streamlit Cloud

1. Faça upload do projeto para um repositório GitHub
2. Conecte o Streamlit Cloud ao repositório
3. Configure as variáveis de ambiente no Streamlit Cloud
4. Implante o aplicativo

## 🔄 Fluxo de Trabalho

1. **Seleção de Biblioteca**: Escolha uma biblioteca do SharePoint
2. **Busca de Arquivos**: O sistema lista arquivos disponíveis
3. **Seleção de Arquivos**: Selecione quais arquivos processar
4. **Processamento**: O sistema baixa e extrai texto
5. **Consulta**: Faça perguntas sobre o conteúdo extraído

## 🤝 Contribuições

Contribuições são bem-vindas! Por favor, siga estas etapas:

1. Faça um fork do projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-funcionalidade`)
3. Commit suas mudanças (`git commit -m 'Adiciona nova funcionalidade'`)
4. Push para a branch (`git push origin feature/nova-funcionalidade`)
5. Abra um Pull Request

## 📝 Licença

Este projeto está licenciado sob a licença MIT.

## 📧 Contato

Para questões ou suporte, entre em contato conosco.

---

Desenvolvido com ❤️ para facilitar o acesso e interpretação de documentos operacionais.
