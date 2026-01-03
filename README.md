# 🤖 Dra. Quantum - Discord Bot Multifuncional

> Um bot Discord completo e inteligente com sistema de IA, moderação automática, boas-vindas personalizadas e muito mais!

[![Discord.py](https://img.shields.io/badge/discord.py-2.3.2-blue?style=flat-square)](https://github.com/Rapptz/discord.py)
[![Python](https://img.shields.io/badge/python-3.8+-green?style=flat-square)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)](#licença)
[![Status](https://img.shields.io/badge/status-beta-yellow?style=flat-square)](#status)

## ✨ Características Principais

### 🤖 Sistema de IA com Groq
- Respostas inteligentes usando **LLaMA 3.1 8B via Groq**
- Personalidade única da "Dra. Quantum" - cientista genial e irônica
- Ativação por menção (`@Dra. Quantum`) ou chamada (`!dra`)
- Detecção automática de palavras-chave ("dra", "doutora", "salve", etc.)

### 👋 Sistema de Boas-vindas
- Mensagens personalizadas ao novo membro entrar
- Atribuição automática de cargo de visitante
- Configuração por servidor
- Embeds bonitas e informativas

### 📢 Sistema de Anúncios
- Envio de anúncios imediatos
- Agendamento de anúncios com data/hora
- Menção automática de cargo específico
- Gerenciamento completo (listar, cancelar, editar)

### 🛡️ AutoModeração Inteligente
- **Anti-links** com whitelist de plataformas autorizadas
- **Anti-convites** para servidores
- **Anti-spam** automático
- Sistema de advertências progressivas
- Expulsão automática ao atingir limite
- Logs detalhados em canal dedicado

### 🔧 Utilitários e Moderação
- `ping` - Latência do bot
- `status` - Informações completas
- `serverinfo` - Dados do servidor
- `userinfo` - Perfil do usuário
- `avatar` - Download de avatares
- `ban` / `kick` - Moderação
- `limpar` - Purge de mensagens
- `slowmode` - Modo lento
- `say` / `embed` - Mensagens customizadas

## 🚀 Início Rápido

### Pré-requisitos
- Python 3.8+
- Token de Bot Discord
- Chave de API Groq

### Instalação

1. **Clone o repositório**
```bash
git clone https://github.com/edigelson-nascimento/Dra.-Quantum---Discord-Bot-Multifuncional.git
cd Dra.-Quantum---Discord-Bot-Multifuncional
```

2. **Instale as dependências**
```bash
pip install -r requirements.txt
```

3. **Configure as credenciais**

Edite `main.py` e adicione suas chaves:

```python
TOKEN = 'seu_token_discord_aqui'
GROQ_API_KEY = 'sua_chave_groq_aqui'
```

**Ou use variáveis de ambiente** (recomendado):

```bash
export DISCORD_TOKEN='seu_token'
export GROQ_API_KEY='sua_chave'
```

4. **Inicie o bot**
```bash
python main.py
```

## 📖 Como Usar

### Comandos de Setup

```bash
# Configurar boas-vindas
!setup welcome #canal-boas-vindas @cargo-visitante Bem-vindo {user}!

# Configurar anúncios
!setup announcements #canal-anuncios @cargo-importante

# Configurar AutoMod
!setup automod #canal-logs
```

### Comandos de Anúncios

```bash
# Enviar anúncio imediato
!anuncio enviar Título Importante | Conteúdo da mensagem aqui

# Agendar anúncio
!anuncio agendar 25/12/2024 18:00 Natal | Feliz Natal a todos!

# Listar agendados
!anuncio listar

# Cancelar anúncio
!anuncio cancelar 1
```

### Comandos de IA

```bash
# Comando direto
!dra Como fazer um buraco negro caseiro?

# Menção ao bot
@Dra. Quantum Qual é o sentido da vida?

# Palavra-chave
Oi dra, tudo bem?
Salve, Doutora!
```

### Comandos de Moderação

```bash
# Advertir usuário
!automod advertir @usuario Spam

# Ver advertências
!automod advertencias @usuario

# Limpar advertências
!automod limpar @usuario

# Banir
!ban @usuario Comportamento tóxico

# Expulsar
!kick @usuario Violação de regras

# Purge
!limpar 10
```

## ⚙️ Configuração Avançada

### Variáveis de Ambiente (.env)

```env
DISCORD_TOKEN=seu_token_aqui
GROQ_API_KEY=sua_chave_groq_aqui
BOT_PREFIX=/
```

### Personalizar Personalidade da IA

Edite a função `gerar_resposta()` em `main.py`:

```python
prompt = f"""Você é a Dra. Quantum: ...
[Customize aqui a personalidade]
"""
```

### Banco de Dados

O bot usa **SQLite** (`quantum.db`) automaticamente. Tabelas criadas:
- `server_config` - Configurações por servidor
- `announcement_channels` - Canais de anúncios
- `scheduled_announcements` - Anúncios agendados
- `deleted_messages` - Log de deletadas
- `automod_config` - Configuração de AutoMod
- `warnings` - Advertências de usuários

## 📊 Estrutura do Projeto

```
dra-quantum-bot/
├── main.py              # Arquivo principal do bot
├── requirements.txt     # Dependências Python
├── README.md           # Este arquivo
├── LICENSE             # Licença MIT
└── quantum.db          # Banco de dados (criado automaticamente)
```

## 🔌 APIs Utilizadas

- **Discord.py** - Interação com Discord
- **Groq API** - IA LLaMA 3.1 8B
- **SQLite** - Persistência de dados

## 📝 Licença

Este projeto está licenciado sob a **Licença MIT**. Veja o arquivo [LICENSE](LICENSE) para mais detalhes.

## 👨‍💻 Desenvolvedor

Desenvolvido por **hazardlabs**

- 🌐 Website: [discord.gg/74bxyVFGPF](https://discord.gg/74bxyVFGPF)
- 📧 Suporte: Entre em contato pelo servidor Discord

## ⚠️ Aviso de Segurança

**IMPORTANTE:** Nunca compartilhe seus tokens ou chaves de API!

- Nunca faça commit de `.env` com credenciais reais
- Use variáveis de ambiente em produção
- Revoque tokens comprometidos imediatamente
- Considere usar secrets em bots hospedados

## 🤝 Contribuições

Contribuições são bem-vindas! Se encontrar bugs ou tiver sugestões:

1. Abra uma **Issue** descrevendo o problema
2. Faça um **Fork** do projeto
3. Crie uma branch para sua feature (`git checkout -b feature/MinhaFeature`)
4. Commit suas mudanças (`git commit -m 'Adiciona MinhaFeature'`)
5. Push para a branch (`git push origin feature/MinhaFeature`)
6. Abra um **Pull Request**

## 🐛 Reportar Bugs

Encontrou um bug? Abra uma [Issue](https://github.com/edigelson-nascimento/Dra.-Quantum---Discord-Bot-Multifuncional/issues) com:

- Descrição detalhada do problema
- Passos para reproduzir
- Comportamento esperado
- Logs de erro (se houver)

## 📚 Documentação Adicional

- [Discord.py Docs](https://discordpy.readthedocs.io/)
- [Groq API Docs](https://groq.com/groqcloud/)
- [Discord Developer Portal](https://discord.com/developers)

## 🎯 Roadmap

- [ ] Suporte para mais idiomas
- [ ] Comandos de música
- [ ] Sistema de economia
- [ ] Integração com OpenAI GPT
- [ ] Dashboard web
- [ ] Backup automático de dados
- [ ] Mais filtros de AutoMod

## 📄 Changelog

### v1.0.0-beta
- ✅ Sistema inicial de IA com Groq
- ✅ Boas-vindas personalizadas
- ✅ Sistema de anúncios agendados
- ✅ AutoModeração completa
- ✅ Comandos utilitários
- ✅ Moderação avançada

## 📧 Suporte

Precisa de ajuda? Entre em contato:

- **Discord**: [discord.gg/74bxyVFGPF](https://discord.gg/74bxyVFGPF)
- **Issues**: Use o sistema de issues do GitHub

## ⭐ Dê uma Estrela!

Se este projeto foi útil para você, considere dar uma ⭐ no GitHub!

---

**Desenvolvido com ❤️ por ed**
