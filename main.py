
import discord
from discord.ext import commands, tasks
import sqlite3
import datetime
import asyncio
import time
import platform
import random
from discord import app_commands
from openai import OpenAI
import os

# ===================== CONFIGURAÇÃO =====================
TOKEN = ''  # ← COLOQUE SEU TOKEN AQUI
PREFIX = '/'
GROQ_API_KEY = ''  # ← SUA CHAVE REAL AQUI

# Configure o cliente Groq
try:
    groq_client = OpenAI(
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    print("✅ API do Groq configurada com sucesso!")
except Exception as e:
    print(f"❌ Erro ao configurar Groq API: {e}")

# ===================== CRÉDITOS =====================
DEVELOPER_NAME = "hazardlabs"
DEVELOPER_URL = "https://discord.gg/74bxyVFGPF"
BOT_VERSION = "beta"
BOT_NAME = "Dra. Quantum"
BOT_DESCRIPTION = "🤖 Bot multifuncional com sistema de IA, Boas-vindas, Anúncios e Moderação"
BOT_ACTIVITY = "👥 Gerenciando servidores"

# ===================== INTENTS =====================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.guilds = True

# ===================== CLASSE DO BOT =====================
class DraQuantum(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=PREFIX,
            intents=intents,
            help_command=None,
            case_insensitive=True
        )
        # Banco de dados
        self.db = sqlite3.connect('quantum.db', check_same_thread=False)
        self.init_database()
        
        # Informações
        self.start_time = datetime.datetime.now()
        self.developer_name = DEVELOPER_NAME
        self.developer_url = DEVELOPER_URL
        self.version = BOT_VERSION
        self.bot_name = BOT_NAME
        self.description = BOT_DESCRIPTION
        self.activity_type = "playing"  # playing, streaming, listening, watching
        self.activity_text = BOT_ACTIVITY
    
    def init_database(self):
        """Inicializa todas as tabelas do banco de dados"""
        cursor = self.db.cursor()
        
        # Tabela de configuração do servidor
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS server_config (
                guild_id INTEGER PRIMARY KEY,
                welcome_channel_id INTEGER,
                welcome_message TEXT,
                visitor_role_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de canais de anúncios
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS announcement_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER,
                mention_role TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de anúncios agendados
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scheduled_announcements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                message TEXT,
                send_at TIMESTAMP,
                sent BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de mensagens deletadas
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS deleted_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                channel_id INTEGER,
                author_id INTEGER,
                content TEXT,
                deleted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de configuração AutoMod
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS automod_config (
                guild_id INTEGER PRIMARY KEY,
                enabled BOOLEAN DEFAULT 0,
                anti_links BOOLEAN DEFAULT 0,
                anti_invites BOOLEAN DEFAULT 0,
                anti_spam BOOLEAN DEFAULT 0,
                max_warnings INTEGER DEFAULT 3,
                log_channel_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Tabela de advertências
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                user_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.db.commit()
        print("📊 Banco de dados inicializado")
    
    def get_guild_config(self, guild_id):
        """Obtém a configuração do servidor"""
        cursor = self.db.cursor()
        cursor.execute(
            'SELECT * FROM server_config WHERE guild_id = ?',
            (guild_id,)
        )
        return cursor.fetchone()
    
    def update_guild_config(self, guild_id, **kwargs):
        """Atualiza a configuração do servidor"""
        cursor = self.db.cursor()
        
        # Verifica se já existe configuração
        cursor.execute(
            'SELECT * FROM server_config WHERE guild_id = ?',
            (guild_id,)
        )
        
        if cursor.fetchone():
            # Atualiza
            fields = ', '.join([f'{key} = ?' for key in kwargs.keys()])
            values = list(kwargs.values())
            values.append(guild_id)
            
            cursor.execute(
                f'UPDATE server_config SET {fields} WHERE guild_id = ?',
                values
            )
        else:
            # Insere novo
            keys = ', '.join(kwargs.keys())
            placeholders = ', '.join(['?'] * len(kwargs))
            values = list(kwargs.values()) + [guild_id]
            
            cursor.execute(
                f'INSERT INTO server_config (guild_id, {keys}) VALUES (?, {placeholders})',
                [guild_id] + list(kwargs.values())
            )
        
        self.db.commit()
    
    def get_automod_config(self, guild_id):
        """Obtém configuração do AutoMod"""
        cursor = self.db.cursor()
        cursor.execute(
            'SELECT * FROM automod_config WHERE guild_id = ?',
            (guild_id,)
        )
        return cursor.fetchone()
    
    def update_automod_config(self, guild_id, **kwargs):
        """Atualiza configuração do AutoMod"""
        cursor = self.db.cursor()
        
        cursor.execute(
            'SELECT * FROM automod_config WHERE guild_id = ?',
            (guild_id,)
        )
        
        if cursor.fetchone():
            # Atualiza
            fields = ', '.join([f'{key} = ?' for key in kwargs.keys()])
            values = list(kwargs.values())
            values.append(guild_id)
            
            cursor.execute(
                f'UPDATE automod_config SET {fields} WHERE guild_id = ?',
                values
            )
        else:
            # Insere novo
            keys = ', '.join(kwargs.keys())
            placeholders = ', '.join(['?'] * len(kwargs))
            values = list(kwargs.values()) + [guild_id]
            
            cursor.execute(
                f'INSERT INTO automod_config (guild_id, {keys}) VALUES (?, {placeholders})',
                [guild_id] + list(kwargs.values())
            )
        
        self.db.commit()
    
    async def setup_hook(self):
        """Configurações iniciais do bot"""
        print("⚙️ Configurando comandos...")
        # Inicia a verificação de anúncios agendados
        asyncio.create_task(self.check_scheduled_announcements())
        # Inicia a verificação de status aleatório
        asyncio.create_task(self.change_status_loop())
    
    async def change_status_loop(self):
        """Muda o status do bot periodicamente"""
        await self.wait_until_ready()
        
        statuses = [
            {"type": "playing", "text": f"{PREFIX}ajuda para comandos"},
            {"type": "playing", "text": "👥 Gerenciando servidores"},
            {"type": "playing", "text": f"Versão {self.version}"},
            {"type": "watching", "text": f"{len(self.guilds)} servidores"},
            {"type": "listening", "text": "discord.gg/74bxyVFGPF"},
            {"type": "playing", "text": "Desenvolvido por hazardlabs"}
        ]
        
        while not self.is_closed():
            try:
                status = random.choice(statuses)
                
                if status["type"] == "playing":
                    activity = discord.Game(name=status["text"])
                elif status["type"] == "watching":
                    activity = discord.Activity(type=discord.ActivityType.watching, name=status["text"])
                elif status["type"] == "listening":
                    activity = discord.Activity(type=discord.ActivityType.listening, name=status["text"])
                elif status["type"] == "streaming":
                    activity = discord.Streaming(name=status["text"], url="https://twitch.tv/hazardlabs")
                else:
                    activity = discord.Game(name=status["text"])
                
                await self.change_presence(activity=activity)
                
                # Espera 2 minutos antes de mudar novamente
                await asyncio.sleep(120)
                
            except Exception as e:
                print(f"Erro ao mudar status: {e}")
                await asyncio.sleep(120)
    
    async def on_ready(self):
        """Executado quando o bot está pronto"""
        print(f'{"="*50}')
        print(f'⚡ {self.bot_name} está online!')
        print(f'{"="*50}')
        print(f'🆔 ID: {self.user.id}')
        print(f'📚 Prefixo: {PREFIX}')
        print(f'👥 Conectado em {len(self.guilds)} servidores')
        print(f'👨‍💻 Desenvolvedor: {self.developer_name}')
        print(f'🌐 Website: {self.developer_url}')
        print(f'🔧 Versão: {self.version}')
        print(f'{"="*50}')
        
        # Sincroniza comandos slash
        try:
            synced = await self.tree.sync()
            print(f"✅ {len(synced)} comandos slash sincronizados")
        except Exception as e:
            print(f"❌ Erro ao sincronizar comandos: {e}")
    
    async def on_command_error(self, ctx, error):
        """Tratamento de erros de comandos"""
        if isinstance(error, commands.CommandNotFound):
            return
        
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send(f"❌ {ctx.author.mention}, você não tem permissão para usar este comando!")
        
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Uso correto: `{PREFIX}{ctx.command.name} {ctx.command.signature}`")
        
        else:
            print(f"Erro: {error}")
    
    # ===================== AUTO-MODERAÇÃO =====================
    async def on_message(self, message):
        """Sistema de Auto-Moderação"""
        if message.author.bot:
            return
        
        if message.guild:
            config = self.get_automod_config(message.guild.id)
            
            if config and config[1]:  # enabled
                await self.check_automod_rules(message, config)
        
        await self.process_commands(message)
    
    async def check_automod_rules(self, message, config):
        """Verifica as regras do AutoMod"""
        content = message.content.lower()

        # ========================= ANTI-LINKS =========================
        if config[2] and any(x in content for x in ["http://", "https://", "www."]):

            links_permitidos = {
                "discord.gg",
                "discord.com/invite",
                "youtube.com",
                "youtu.be",
                "github.com",
                "twitch.tv",
                "tenor.com",
                "giphy.com",
                "imgur.com",
                "reddit.com",
                "twitter.com",
                "x.com",
                "steamcommunity.com",
                "store.steampowered.com"
            }

            # Verifica se algum link permitido aparece na mensagem
            permitido = any(link in content for link in links_permitidos)

            if not permitido:
                try:
                    await message.delete()
                except:
                    pass

                await message.channel.send(
                    f"❌ {message.author.mention}, links não são permitidos aqui! (Apenas plataformas autorizadas)",
                    delete_after=5
                )

                await self.log_automod_action(message, "Envio de link bloqueado")
                await self.add_warning(
                    message.guild.id,
                    message.author.id,
                    self.user.id,
                    "Envio de link não permitido"
                )
                return

        # ==============================================================
    
    async def log_automod_action(self, message, reason):
        """Registra ação do AutoMod no canal de logs"""
        config = self.get_automod_config(message.guild.id)
        if config and config[6]:  # log_channel_id
            channel = message.guild.get_channel(config[6])
            if channel:
                embed = discord.Embed(
                    title="🚨 AutoMod - Ação Tomada",
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.now()
                )
                embed.add_field(name="👤 Usuário", value=f"{message.author.mention} ({message.author.id})", inline=False)
                embed.add_field(name="📝 Canal", value=message.channel.mention, inline=False)
                embed.add_field(name="⚠️ Motivo", value=reason, inline=False)
                embed.add_field(name="🗑️ Mensagem", value=f"```{message.content[:100]}...```", inline=False)
                
                await channel.send(embed=embed)
    
    async def add_warning(self, guild_id, user_id, moderator_id, reason):
        """Adiciona uma advertência ao usuário"""
        cursor = self.db.cursor()
        cursor.execute(
            '''INSERT INTO warnings (guild_id, user_id, moderator_id, reason) 
            VALUES (?, ?, ?, ?)''',
            (guild_id, user_id, moderator_id, reason)
        )
        self.db.commit()
        
        # Verifica se atingiu o limite de advertências
        cursor.execute(
            'SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?',
            (guild_id, user_id)
        )
        count = cursor.fetchone()[0]
        
        config = self.get_automod_config(guild_id)
        if config and count >= config[5]:  # max_warnings
            guild = self.get_guild(guild_id)
            if guild:
                member = guild.get_member(user_id)
                if member:
                    try:
                        await member.kick(reason=f"Limite de advertências atingido: {count}/{config[5]}")
                        
                        # Log no canal
                        if config[6]:
                            channel = guild.get_channel(config[6])
                            if channel:
                                embed = discord.Embed(
                                    title="🚨 AutoMod - Usuário Expulso",
                                    description=f"**{member.name}** foi expulso por atingir o limite de advertências.",
                                    color=discord.Color.dark_red(),
                                    timestamp=datetime.datetime.now()
                                )
                                embed.add_field(name="👤 Usuário", value=f"{member.mention} ({member.id})")
                                embed.add_field(name="⚠️ Advertências", value=f"{count}/{config[5]}")
                                embed.add_field(name="📋 Motivo", value="Limite de advertências excedido")
                                
                                await channel.send(embed=embed)
                    except:
                        pass
    
    # ===================== SISTEMA DE ANÚNCIOS AGENDADOS =====================
    async def check_scheduled_announcements(self):
        """Verifica e envia anúncios agendados periodicamente"""
        await self.wait_until_ready()
        
        while not self.is_closed():
            try:
                cursor = self.db.cursor()
                now = datetime.datetime.now()
                
                # Busca anúncios pendentes
                cursor.execute(
                    '''SELECT id, guild_id, channel_id, message 
                    FROM scheduled_announcements 
                    WHERE send_at <= ? AND sent = 0''',
                    (now,)
                )
                
                announcements = cursor.fetchall()
                
                for ann_id, guild_id, channel_id, message in announcements:
                    guild = self.get_guild(guild_id)
                    
                    if guild:
                        channel = guild.get_channel(channel_id)
                        
                        if channel:
                            # Separa título e mensagem
                            if "|" in message:
                                title, content = message.split("|", 1)
                                title = title.strip()
                                content = content.strip()
                            else:
                                title = "📢 Anúncio Agendado"
                                content = message
                            
                            # Cria embed
                            embed = discord.Embed(
                                title=title,
                                description=content,
                                color=discord.Color.gold(),
                                timestamp=now
                            )
                            
                            # Obtém menção do cargo
                            cursor.execute(
                                'SELECT mention_role FROM announcement_channels WHERE guild_id = ?',
                                (guild_id,)
                            )
                            config = cursor.fetchone()
                            mention = config[0] if config else "@everyone"
                            
                            # Envia
                            await channel.send(f"{mention}", embed=embed)
                            
                            # Marca como enviado
                            cursor.execute(
                                'UPDATE scheduled_announcements SET sent = 1 WHERE id = ?',
                                (ann_id,)
                            )
                            self.db.commit()
                
                # Espera 60 segundos antes de verificar novamente
                await asyncio.sleep(60)
                
            except Exception as e:
                print(f"Erro ao verificar anúncios agendados: {e}")
                await asyncio.sleep(60)

# ===================== CRIAÇÃO DO BOT =====================
bot = DraQuantum()

# ===================== COMANDOS DE BOAS-VINDAS =====================
@bot.hybrid_group(name="setup", description="Configuração do servidor")
async def setup_group(ctx):
    """Grupo de comandos de setup"""
    if ctx.invoked_subcommand is None:
        embed = discord.Embed(
            title="⚙️ Configuração do Servidor",
            description="Comandos disponíveis:",
            color=discord.Color(0xff699c)
        )
        embed.add_field(
            name="📝 Configurar Boas-vindas",
            value="`!setup welcome [#canal] [@cargo-visitante] [texto]`",
            inline=False
        )
        embed.add_field(
            name="📢 Configurar Anúncios",
            value="`!setup announcements [#canal] [@cargo]`",
            inline=False
        )
        embed.add_field(
            name="🛡️ Configurar AutoMod",
            value="`!setup automod [#canal-log]`",
            inline=False
        )
        await ctx.send(embed=embed)

@setup_group.command(name="welcome", description="Configura o sistema de boas-vindas")
@commands.has_permissions(administrator=True)
async def setup_welcome(ctx, channel: discord.TextChannel, visitor_role: discord.Role = None, *, texto: str = None):
    """Configura o canal de boas-vindas com texto personalizado"""
    try:
        bot.update_guild_config(
            ctx.guild.id,
            welcome_channel_id=channel.id,
            welcome_message=texto,
            visitor_role_id=visitor_role.id if visitor_role else None
        )
        
        embed = discord.Embed(
            title="✅ Sistema de Boas-vindas Configurado",
            description=f"Mensagens de boas-vindas serão enviadas em: {channel.mention}",
            color=discord.Color(0xff699c)
        )
        
        if visitor_role:
            embed.add_field(name="🎭 Cargo de Visitante", value=visitor_role.mention)
        
        if texto:
            embed.add_field(name="📝 Mensagem Personalizada", value=texto, inline=False)
        else:
            embed.add_field(name="📝 Mensagem Padrão", value=f"Bem-vindo(a) {{user}} ao {{ctx.guild_name}}!", inline=False)
        
        embed.add_field(name="👮 Configurado por", value=ctx.author.mention)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Erro ao configurar: {e}")

@setup_group.command(name="announcements", description="Configura o canal de anúncios")
@commands.has_permissions(administrator=True)
async def setup_announcements(ctx, channel: discord.TextChannel, role: discord.Role = None):
    """Configura o canal de anúncios"""
    try:
        cursor = bot.db.cursor()
        mention_role = role.mention if role else "@everyone"
        
        cursor.execute(
            'SELECT * FROM announcement_channels WHERE guild_id = ?',
            (ctx.guild.id,)
        )
        
        if cursor.fetchone():
            cursor.execute(
                '''UPDATE announcement_channels 
                SET channel_id = ?, mention_role = ?
                WHERE guild_id = ?''',
                (channel.id, mention_role, ctx.guild.id)
            )
        else:
            cursor.execute(
                '''INSERT INTO announcement_channels 
                (guild_id, channel_id, mention_role) 
                VALUES (?, ?, ?)''',
                (ctx.guild.id, channel.id, mention_role)
            )
        
        bot.db.commit()
        
        embed = discord.Embed(
            title="✅ Canal de Anúncios Configurado",
            description=f"Anúncios serão enviados em: {channel.mention}",
            color=discord.Color(0xff699c)
        )
        embed.add_field(name="📢 Menção", value=mention_role)
        embed.add_field(name="👮 Configurado por", value=ctx.author.mention)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Erro ao configurar: {e}")

@setup_group.command(name="automod", description="Configura o sistema de AutoMod")
@commands.has_permissions(administrator=True)
async def setup_automod(ctx, log_channel: discord.TextChannel = None):
    """Configura o sistema de AutoModeração"""
    try:
        bot.update_automod_config(
            ctx.guild.id,
            enabled=True,
            anti_links=True,
            anti_invites=True,
            anti_spam=True,
            max_warnings=3,
            log_channel_id=log_channel.id if log_channel else None
        )
        
        embed = discord.Embed(
            title="✅ AutoMod Configurado",
            description="Sistema de moderação automática ativado!",
            color=discord.Color(0xff699c)
        )
        
        embed.add_field(name="🔗 Anti-Links", value="✅ Ativado", inline=True)
        embed.add_field(name="🎫 Anti-Invites", value="✅ Ativado", inline=True)
        embed.add_field(name="⚠️ Anti-Spam", value="✅ Ativado", inline=True)
        embed.add_field(name="📊 Máx. Advertências", value="3", inline=True)
        
        if log_channel:
            embed.add_field(name="📝 Canal de Logs", value=log_channel.mention, inline=False)
        
        embed.add_field(name="👮 Configurado por", value=ctx.author.mention)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Erro ao configurar: {e}")

# Evento de boas-vindas
@bot.event
async def on_member_join(member):
    """Envia mensagem de boas-vindas quando um membro entra"""
    config = bot.get_guild_config(member.guild.id)
    
    if config:
        channel_id = config[1]  # welcome_channel_id
        if channel_id:
            channel = member.guild.get_channel(channel_id)
            if channel:
                # Mensagem personalizada ou padrão
                welcome_message = config[2] if config[2] else "Bem-vindo(a) {user} ao {member.guild.name}!"
                welcome_message = welcome_message.replace("{user}", member.mention)
                welcome_message = welcome_message.replace("{server}", member.guild.name)
                welcome_message = welcome_message.replace("{membercount}", str(member.guild.member_count))
                
                embed = discord.Embed(
                    title=f"👋 Bem-vindo(a) ao {member.guild.name}!",
                    description=welcome_message,
                    color=discord.Color(0xff699c),
                    timestamp=datetime.datetime.now()
                )
                embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
                embed.set_footer(text=f"ID: {member.id} | {member.guild.member_count}º membro")
                
                await channel.send(embed=embed)
        
        # Atribui cargo de visitante
        role_id = config[3]  # visitor_role_id
        if role_id:
            role = member.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role)
                except:
                    pass

# ===================== COMANDOS DE ANÚNCIOS =====================
@bot.hybrid_group(name="anuncio", description="Comandos de anúncios")
async def announcement_group(ctx):
    """Grupo de comandos de anúncios"""
    if ctx.invoked_subcommand is None:
        embed = discord.Embed(
            title="📢 Sistema de Anúncios",
            description="Comandos disponíveis:",
            color=discord.Color(0xff699c)
        )
        embed.add_field(
            name="🚀 Enviar Anúncio",
            value="`!anuncio enviar [título] | [mensagem]`",
            inline=False
        )
        embed.add_field(
            name="⏰ Agendar Anúncio",
            value="`!anuncio agendar [dd/mm/aaaa hh:mm] [título] | [mensagem]`",
            inline=False
        )
        embed.add_field(
            name="📋 Listar Agendados",
            value="`!anuncio listar`",
            inline=False
        )
        embed.add_field(
            name="❌ Cancelar Anúncio",
            value="`!anuncio cancelar [id]`",
            inline=False
        )
        await ctx.send(embed=embed)

@announcement_group.command(name="enviar", description="Envia um anúncio")
@commands.has_permissions(administrator=True)
async def send_announcement(ctx, *, content: str):
    """Envia um anúncio no canal configurado"""
    try:
        if "|" in content:
            title, message = content.split("|", 1)
            title = title.strip()
            message = message.strip()
        else:
            title = "📢 Anúncio Importante"
            message = content
        
        cursor = bot.db.cursor()
        cursor.execute(
            'SELECT channel_id, mention_role FROM announcement_channels WHERE guild_id = ?',
            (ctx.guild.id,)
        )
        
        config = cursor.fetchone()
        
        if not config:
            await ctx.send("❌ Nenhum canal de anúncios configurado! Use `!setup announcements` primeiro.")
            return
        
        channel_id, mention_role = config
        channel = ctx.guild.get_channel(channel_id)
        
        if not channel:
            await ctx.send("❌ Canal não encontrado!")
            return
        
        embed = discord.Embed(
            title=title,
            description=message,
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(
            text=f"Anúncio por {ctx.author.name}",
            icon_url=ctx.author.avatar.url if ctx.author.avatar else None
        )
        
        await channel.send(f"{mention_role}", embed=embed)
        
        confirm_embed = discord.Embed(
            title="✅ Anúncio Enviado",
            description=f"Anúncio publicado em {channel.mention}",
            color=discord.Color(0xff699c)
        )
        await ctx.send(embed=confirm_embed)
        
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

@announcement_group.command(name="agendar", description="Agenda um anúncio")
@commands.has_permissions(administrator=True)
async def schedule_announcement(ctx, date_time: str, *, content: str):
    """Agenda um anúncio"""
    try:
        send_at = datetime.datetime.strptime(date_time, "%d/%m/%Y %H:%M")
        now = datetime.datetime.now()
        
        if send_at <= now:
            await ctx.send("❌ A data/hora deve ser futura!")
            return
        
        if "|" in content:
            title, message = content.split("|", 1)
            title = title.strip()
            message = message.strip()
        else:
            title = "📢 Anúncio Importante"
            message = content
        
        cursor = bot.db.cursor()
        cursor.execute(
            'SELECT channel_id FROM announcement_channels WHERE guild_id = ?',
            (ctx.guild.id,)
        )
        
        config = cursor.fetchone()
        
        if not config:
            await ctx.send("❌ Nenhum canal de anúncios configurado!")
            return
        
        channel_id = config[0]
        
        cursor.execute(
            '''INSERT INTO scheduled_announcements 
            (guild_id, channel_id, message, send_at) 
            VALUES (?, ?, ?, ?)''',
            (ctx.guild.id, channel_id, f"{title}|{message}", send_at)
        )
        bot.db.commit()
        
        announcement_id = cursor.lastrowid
        
        embed = discord.Embed(
            title="✅ Anúncio Agendado",
            description=f"Agendado para {send_at.strftime('%d/%m/%Y às %H:%M')}",
            color=discord.Color(0xff699c)
        )
        embed.add_field(name="📌 ID", value=f"`{announcement_id}`")
        embed.add_field(name="✍️ Autor", value=ctx.author.mention)
        
        await ctx.send(embed=embed)
        
    except ValueError:
        await ctx.send("❌ Formato de data inválido! Use: `dd/mm/aaaa hh:mm`")
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

@announcement_group.command(name="listar", description="Lista anúncios agendados")
@commands.has_permissions(administrator=True)
async def list_announcements(ctx):
    """Lista anúncios agendados"""
    try:
        cursor = bot.db.cursor()
        cursor.execute(
            '''SELECT id, message, send_at 
            FROM scheduled_announcements 
            WHERE guild_id = ? AND sent = 0
            ORDER BY send_at''',
            (ctx.guild.id,)
        )
        
        announcements = cursor.fetchall()
        
        if not announcements:
            await ctx.send("📭 Nenhum anúncio agendado.")
            return
        
        embed = discord.Embed(
            title="📋 Anúncios Agendados",
            description=f"Total: {len(announcements)}",
            color=discord.Color(0xff699c)
        )
        
        for ann_id, message, send_at in announcements:
            if "|" in message:
                title, content = message.split("|", 1)
                title = title[:50] + "..." if len(title) > 50 else title
            else:
                title = message[:50] + "..." if len(message) > 50 else message
            
            send_time = datetime.datetime.strptime(send_at, "%Y-%m-%d %H:%M:%S")
            time_str = send_time.strftime("%d/%m %H:%M")
            
            embed.add_field(
                name=f"📌 ID: {ann_id} - {time_str}",
                value=f"**{title}**",
                inline=False
            )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

@announcement_group.command(name="cancelar", description="Cancela um anúncio agendado")
@commands.has_permissions(administrator=True)
async def cancel_announcement(ctx, announcement_id: int):
    """Cancela um anúncio agendado"""
    try:
        cursor = bot.db.cursor()
        cursor.execute(
            'SELECT id FROM scheduled_announcements WHERE id = ? AND guild_id = ?',
            (announcement_id, ctx.guild.id)
        )
        
        if not cursor.fetchone():
            await ctx.send(f"❌ Anúncio não encontrado!")
            return
        
        cursor.execute(
            'DELETE FROM scheduled_announcements WHERE id = ?',
            (announcement_id,)
        )
        bot.db.commit()
        
        embed = discord.Embed(
            title="✅ Anúncio Cancelado",
            description=f"Anúncio `{announcement_id}` cancelado.",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

# ===================== NOVOS COMANDOS (AUTO-MOD) =====================
@bot.hybrid_group(name="automod", description="Comandos de AutoModeração")
async def automod_group(ctx):
    """Grupo de comandos de AutoMod"""
    if ctx.invoked_subcommand is None:
        config = bot.get_automod_config(ctx.guild.id)
        
        embed = discord.Embed(
            title="🛡️ Sistema de AutoModeração",
            description="Comandos disponíveis:",
            color=discord.Color(0xff699c)
        )
        
        if config and config[1]:
            embed.add_field(name="📊 Status", value="✅ **ATIVADO**", inline=False)
            embed.add_field(name="🔗 Anti-Links", value="✅" if config[2] else "❌", inline=True)
            embed.add_field(name="🎫 Anti-Invites", value="✅" if config[3] else "❌", inline=True)
            embed.add_field(name="⚠️ Anti-Spam", value="✅" if config[4] else "❌", inline=True)
            embed.add_field(name="📊 Máx. Advertências", value=f"`{config[5]}`", inline=True)
        else:
            embed.add_field(name="📊 Status", value="❌ **DESATIVADO**", inline=False)
        
        embed.add_field(
            name="📝 Comandos",
            value="`!automod advertir [@usuário] [motivo]` - Adverte um usuário\n"
                  "`!automod advertências [@usuário]` - Ver advertências\n"
                  "`!automod limpar [@usuário]` - Limpa advertências\n"
                  "`!automod config` - Ver configuração\n"
                  "`!automod ativar` - Ativar AutoMod\n"
                  "`!automod desativar` - Desativar AutoMod",
            inline=False
        )
        
        await ctx.send(embed=embed)

@automod_group.command(name="advertir", description="Adverte um usuário")
@commands.has_permissions(manage_messages=True)
async def warn_user(ctx, member: discord.Member, *, motivo: str = "Sem motivo especificado"):
    """Adverte um usuário"""
    if member == ctx.author:
        await ctx.send("❌ Você não pode advertir a si mesmo!", ephemeral=True)
        return
    
    try:
        await bot.add_warning(ctx.guild.id, member.id, ctx.author.id, motivo)
        
        # Conta advertências
        cursor = bot.db.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?',
            (ctx.guild.id, member.id)
        )
        count = cursor.fetchone()[0]
        
        embed = discord.Embed(
            title="⚠️ Usuário Advertido",
            description=f"**{member.name}** recebeu uma advertência.",
            color=discord.Color.orange()
        )
        embed.add_field(name="👮 Moderador", value=ctx.author.mention)
        embed.add_field(name="📝 Motivo", value=motivo)
        embed.add_field(name="📊 Total de Advertências", value=f"`{count}`", inline=False)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

@automod_group.command(name="advertencias", description="Ver advertências de um usuário")
@commands.has_permissions(manage_messages=True)
async def check_warnings(ctx, member: discord.Member = None):
    """Ver advertências de um usuário"""
    if member is None:
        member = ctx.author
    
    cursor = bot.db.cursor()
    cursor.execute(
        '''SELECT reason, created_at, moderator_id 
        FROM warnings 
        WHERE guild_id = ? AND user_id = ?
        ORDER BY created_at DESC''',
        (ctx.guild.id, member.id)
    )
    
    warnings = cursor.fetchall()
    
    embed = discord.Embed(
        title=f"📋 Advertências de {member.name}",
        description=f"Total: **{len(warnings)}** advertências",
        color=discord.Color.orange()
    )
    
    if warnings:
        for i, (reason, created_at, moderator_id) in enumerate(warnings[:5], 1):
            moderator = ctx.guild.get_member(moderator_id)
            mod_name = moderator.name if moderator else "Sistema"
            
            created = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
            time_str = created.strftime("%d/%m %H:%M")
            
            embed.add_field(
                name=f"#{i} - {time_str}",
                value=f"**Motivo:** {reason}\n**Por:** {mod_name}",
                inline=False
            )
    else:
        embed.add_field(name="✅ Limpo", value="Este usuário não possui advertências.", inline=False)
    
    await ctx.send(embed=embed)

@automod_group.command(name="limpar", description="Limpa advertências de um usuário")
@commands.has_permissions(administrator=True)
async def clear_warnings(ctx, member: discord.Member):
    """Limpa todas as advertências de um usuário"""
    try:
        cursor = bot.db.cursor()
        cursor.execute(
            'SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?',
            (ctx.guild.id, member.id)
        )
        count = cursor.fetchone()[0]
        
        if count == 0:
            await ctx.send(f"❌ {member.name} não possui advertências para limpar.")
            return
        
        cursor.execute(
            'DELETE FROM warnings WHERE guild_id = ? AND user_id = ?',
            (ctx.guild.id, member.id)
        )
        bot.db.commit()
        
        embed = discord.Embed(
            title="✅ Advertências Limpas",
            description=f"**{count}** advertências de **{member.name}** foram removidas.",
            color=discord.Color(0xff699c)
        )
        embed.add_field(name="👮 Moderador", value=ctx.author.mention)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

@automod_group.command(name="config", description="Ver configuração do AutoMod")
@commands.has_permissions(manage_messages=True)
async def automod_config(ctx):
    """Mostra configuração do AutoMod"""
    config = bot.get_automod_config(ctx.guild.id)
    
    embed = discord.Embed(
        title="⚙️ Configuração do AutoMod",
        color=discord.Color(0xff699c)
    )
    
    if config:
        embed.add_field(name="📊 Status", value="✅ **ATIVADO**" if config[1] else "❌ **DESATIVADO**", inline=False)
        embed.add_field(name="🔗 Anti-Links", value="✅ Ativado" if config[2] else "❌ Desativado", inline=True)
        embed.add_field(name="🎫 Anti-Invites", value="✅ Ativado" if config[3] else "❌ Desativado", inline=True)
        embed.add_field(name="⚠️ Anti-Spam", value="✅ Ativado" if config[4] else "❌ Desativado", inline=True)
        embed.add_field(name="📊 Máx. Advertências", value=f"`{config[5]}`", inline=True)
        
        if config[6]:
            channel = ctx.guild.get_channel(config[6])
            embed.add_field(name="📝 Canal de Logs", value=channel.mention if channel else "❌ Não encontrado", inline=False)
        else:
            embed.add_field(name="📝 Canal de Logs", value="❌ Não configurado", inline=False)
    else:
        embed.add_field(name="📊 Status", value="❌ **NÃO CONFIGURADO**", inline=False)
        embed.description = "Use `!setup automod` para configurar o sistema."
    
    await ctx.send(embed=embed)

@automod_group.command(name="ativar", description="Ativa o sistema de AutoMod")
@commands.has_permissions(administrator=True)
async def enable_automod(ctx):
    """Ativa o sistema de AutoMod"""
    try:
        bot.update_automod_config(ctx.guild.id, enabled=True)
        
        embed = discord.Embed(
            title="✅ AutoMod Ativado",
            description="Sistema de moderação automática foi ativado!",
            color=discord.Color(0xff699c)
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

@automod_group.command(name="desativar", description="Desativa o sistema de AutoMod")
@commands.has_permissions(administrator=True)
async def disable_automod(ctx):
    """Desativa o sistema de AutoMod"""
    try:
        bot.update_automod_config(ctx.guild.id, enabled=False)
        
        embed = discord.Embed(
            title="✅ AutoMod Desativado",
            description="Sistema de moderação automática foi desativado.",
            color=discord.Color(0xff699c)
        )
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

# ===================== COMANDOS UTILITÁRIOS =====================
@bot.hybrid_command(name="ping", description="Mostra a latência do bot")
async def ping(ctx):
    """Mostra latência"""
    api_latency = round(bot.latency * 1000)
    
    start_time = time.time()
    message = await ctx.send("🏓 Pong! Calculando...")
    end_time = time.time()
    
    bot_latency = round((end_time - start_time) * 1000)
    
    embed = discord.Embed(
        title="🏓 Pong!",
        color=discord.Color(0xff699c)
    )
    
    embed.add_field(name="📡 Latência da API", value=f"`{api_latency}ms`", inline=True)
    embed.add_field(name="🤖 Latência do Bot", value=f"`{bot_latency}ms`", inline=True)
    
    delta = datetime.datetime.now() - bot.start_time
    days = delta.days
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    if days > 0:
        uptime = f"`{days}d {hours}h {minutes}m {seconds}s`"
    elif hours > 0:
        uptime = f"`{hours}h {minutes}m {seconds}s`"
    else:
        uptime = f"`{minutes}m {seconds}s`"
    
    embed.add_field(name="⏱️ Uptime", value=uptime, inline=False)
    
    await message.edit(content=None, embed=embed)

@bot.hybrid_command(name="status", description="Mostra status completo do bot")
async def status(ctx):
    """Mostra status do bot"""
    guilds = len(bot.guilds)
    members = sum(guild.member_count for guild in bot.guilds)
    
    embed = discord.Embed(
        title="⚡ Dra. Quantum - Status",
        description=bot.description,
        color=discord.Color(0xff699c),
        timestamp=datetime.datetime.now()
    )
    
    embed.add_field(
        name="🤖 Sobre Mim",
        value=f"**Nome:** {bot.bot_name}\n"
              f"**Versão:** {bot.version}\n"
              f"**Desenvolvedor:** [{bot.developer_name}]({bot.developer_url})\n"
              f"**Prefixo:** `{bot.command_prefix}`",
        inline=False
    )
    
    embed.add_field(
        name="📊 Estatísticas",
        value=f"**Servidores:** `{guilds}`\n"
              f"**Usuários:** `{members}`\n"
              f"**Comandos:** `{len(bot.commands)}`",
        inline=True
    )
    
    delta = datetime.datetime.now() - bot.start_time
    uptime = f"{delta.days}d {delta.seconds//3600}h {(delta.seconds//60)%60}m"
    
    embed.add_field(
        name="⏱️ Sistema",
        value=f"**Uptime:** `{uptime}`\n"
              f"**Latência:** `{round(bot.latency * 1000)}ms`\n"
              f"**Python:** `{platform.python_version()}`\n"
              f"**discord.py:** `{discord.__version__}`",
        inline=True
    )
    
    embed.add_field(
        name="🔧 Recursos",
        value="✅ Sistema de Boas-vindas\n"
              "✅ Sistema de Anúncios\n"
              "✅ AutoModeração\n"
              "✅ Moderação\n"
              "✅ Utilitários",
        inline=True
    )
    
    embed.set_footer(text="Status atualizado em")
    embed.set_thumbnail(url=bot.user.avatar.url if bot.user.avatar else None)
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name="serverinfo", description="Mostra informações do servidor")
async def serverinfo(ctx):
    """Mostra informações do servidor"""
    guild = ctx.guild
    
    total_members = guild.member_count
    bots = sum(member.bot for member in guild.members)
    humans = total_members - bots
    
    embed = discord.Embed(
        title=f"📊 {guild.name}",
        color=discord.Color(0xff699c),
        timestamp=datetime.datetime.now()
    )
    
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    
    embed.add_field(name="👑 Proprietário", value=guild.owner.mention, inline=True)
    embed.add_field(name="🆔 ID", value=f"`{guild.id}`", inline=True)
    embed.add_field(name="📅 Criado", value=f"<t:{int(guild.created_at.timestamp())}:D>", inline=True)
    
    embed.add_field(
        name="👥 Membros",
        value=f"**Total:** `{total_members}`\n"
              f"**Humanos:** `{humans}`\n"
              f"**Bots:** `{bots}`",
        inline=True
    )
    
    embed.add_field(
        name="📁 Canais",
        value=f"**Texto:** `{len(guild.text_channels)}`\n"
              f"**Voz:** `{len(guild.voice_channels)}`\n"
              f"**Cargos:** `{len(guild.roles)}`",
        inline=True
    )
    
    embed.add_field(
        name="📈 Estatísticas",
        value=f"**Boosts:** `{guild.premium_subscription_count}`\n"
              f"**Nível Boost:** `{guild.premium_tier}`\n"
              f"**Emojis:** `{len(guild.emojis)}`",
        inline=True
    )
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name="userinfo", description="Mostra informações de um usuário")
async def userinfo(ctx, member: discord.Member = None):
    """Mostra informações do usuário"""
    if member is None:
        member = ctx.author
    
    roles = [role.mention for role in member.roles if role.name != "@everyone"]
    roles_str = ", ".join(roles) if roles else "Nenhum cargo"
    
    # Advertências
    cursor = bot.db.cursor()
    cursor.execute(
        'SELECT COUNT(*) FROM warnings WHERE guild_id = ? AND user_id = ?',
        (ctx.guild.id, member.id)
    )
    warnings = cursor.fetchone()[0]
    
    embed = discord.Embed(
        title=f"👤 {member.name}",
        color=member.color,
        timestamp=datetime.datetime.now()
    )
    
    embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)
    
    embed.add_field(name="🆔 ID", value=f"`{member.id}`", inline=True)
    embed.add_field(name="🎭 Apelido", value=member.nick if member.nick else "Nenhum", inline=True)
    embed.add_field(name="📅 Conta criada", value=f"<t:{int(member.created_at.timestamp())}:R>", inline=True)
    embed.add_field(name="📅 Entrou aqui", value=f"<t:{int(member.joined_at.timestamp())}:R>", inline=True)
    
    embed.add_field(name="⚠️ Advertências", value=f"`{warnings}`", inline=True)
    embed.add_field(name="🤖 É Bot?", value="Sim" if member.bot else "Não", inline=True)
    
    if len(roles_str) < 1024:
        embed.add_field(name=f"🎭 Cargos ({len(roles)})", value=roles_str, inline=False)
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name="limpar", description="Limpa mensagens do chat")
@commands.has_permissions(manage_messages=True)
@commands.bot_has_permissions(manage_messages=True)
async def clear(ctx, quantidade: int = 10):
    """Limpa mensagens"""
    if quantidade < 1 or quantidade > 100:
        await ctx.send("❌ Quantidade deve ser entre 1 e 100.", ephemeral=True)
        return
    
    deleted = await ctx.channel.purge(limit=quantidade + 1, check=lambda m: not m.pinned)
    confirm = await ctx.send(f"✅ {len(deleted)-1} mensagens limpas!", delete_after=5)
    
    await asyncio.sleep(5)
    try:
        await confirm.delete()
    except:
        pass

@bot.hybrid_command(name="ban", description="Bane um usuário")
@commands.has_permissions(ban_members=True)
@commands.bot_has_permissions(ban_members=True)
async def ban_user(ctx, member: discord.Member, *, motivo: str = "Sem motivo"):
    """Bane um usuário"""
    if member == ctx.author:
        await ctx.send("❌ Não pode banir a si mesmo!", ephemeral=True)
        return
    
    try:
        await member.ban(reason=f"{ctx.author.name}: {motivo}")
        
        embed = discord.Embed(
            title="✅ Usuário Banido",
            description=f"**{member.name}** foi banido.",
            color=discord.Color.red()
        )
        embed.add_field(name="👮 Moderador", value=ctx.author.mention)
        embed.add_field(name="📝 Motivo", value=motivo)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

@bot.hybrid_command(name="kick", description="Expulsa um usuário")
@commands.has_permissions(kick_members=True)
@commands.bot_has_permissions(kick_members=True)
async def kick_user(ctx, member: discord.Member, *, motivo: str = "Sem motivo"):
    """Expulsa um usuário"""
    if member == ctx.author:
        await ctx.send("❌ Não pode expulsar a si mesmo!", ephemeral=True)
        return
    
    try:
        await member.kick(reason=f"{ctx.author.name}: {motivo}")
        
        embed = discord.Embed(
            title="✅ Usuário Expulso",
            description=f"**{member.name}** foi expulso.",
            color=discord.Color.red()
        )
        embed.add_field(name="👮 Moderador", value=ctx.author.mention)
        embed.add_field(name="📝 Motivo", value=motivo)
        
        await ctx.send(embed=embed)
        
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

@bot.hybrid_command(name="slowmode", description="Define o modo lento")
@commands.has_permissions(manage_channels=True)
async def slowmode(ctx, segundos: int = 0):
    """Define modo lento"""
    if segundos < 0 or segundos > 21600:
        await ctx.send("❌ Segundos devem ser entre 0 e 21600 (6h).", ephemeral=True)
        return
    
    try:
        await ctx.channel.edit(slowmode_delay=segundos)
        
        if segundos == 0:
            await ctx.send("✅ Modo lento desativado!", ephemeral=True)
        else:
            minutes, seconds = divmod(segundos, 60)
            hours, minutes = divmod(minutes, 60)
            
            time_str = []
            if hours > 0:
                time_str.append(f"{hours}h")
            if minutes > 0:
                time_str.append(f"{minutes}m")
            if seconds > 0:
                time_str.append(f"{seconds}s")
            
            await ctx.send(f"✅ Modo lento: {' '.join(time_str)}!", ephemeral=True)
            
    except Exception as e:
        await ctx.send(f"❌ Erro: {e}")

@bot.hybrid_command(name="say", description="Faz o bot enviar uma mensagem")
@commands.has_permissions(administrator=True)
async def say(ctx, *, mensagem: str):
    """Faz o bot enviar uma mensagem"""
    try:
        await ctx.message.delete()
        await ctx.send(mensagem)
    except:
        await ctx.send(mensagem)

@bot.hybrid_command(name="embed", description="Cria uma embed")
@commands.has_permissions(administrator=True)
async def create_embed(ctx, titulo: str, *, descricao: str):
    """Cria uma embed"""
    embed = discord.Embed(
        title=titulo,
        description=descricao,
        color=discord.Color(0xff699c),
        timestamp=datetime.datetime.now()
    )
    embed.set_footer(text=f"Por {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name="avatar", description="Mostra o avatar de um usuário")
async def avatar(ctx, member: discord.Member = None):
    """Mostra avatar"""
    if member is None:
        member = ctx.author
    
    embed = discord.Embed(
        title=f"🖼️ Avatar de {member.name}",
        color=member.color
    )
    embed.set_image(url=member.avatar.url if member.avatar else member.default_avatar.url)
    
    if member.avatar:
        formats = []
        if member.avatar.is_animated():
            formats.append(f"[GIF]({member.avatar.with_format('gif')})")
        formats.append(f"[PNG]({member.avatar.with_format('png')})")
        formats.append(f"[JPG]({member.avatar.with_format('jpg')})")
        
        embed.add_field(name="📥 Download", value=" | ".join(formats), inline=False)
    
    await ctx.send(embed=embed)

@bot.hybrid_command(name="ajuda", description="Mostra todos os comandos")
async def ajuda(ctx):
    """Comando de ajuda"""
    embed = discord.Embed(
        title="📚 Dra. Quantum - Central de Ajuda",
        description=bot.description,
        color=discord.Color(0xff699c)
    )
    
    embed.add_field(
        name="🤖 Sobre o Bot",
        value=f"**Nome:** {bot.bot_name}\n"
              f"**Versão:** {bot.version}\n"
              f"**Desenvolvedor:** [{bot.developer_name}]({bot.developer_url})\n"
              f"**Prefixo:** `{bot.command_prefix}`",
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Configuração",
        value=f"`{bot.command_prefix}setup welcome [#canal] [@cargo] [texto]` - Boas-vindas\n"
              f"`{bot.command_prefix}setup announcements [#canal] [@cargo]` - Anúncios\n"
              f"`{bot.command_prefix}setup automod [#canal-log]` - AutoMod\n"
              f"`{bot.command_prefix}anuncio enviar [título] | [msg]` - Envia anúncio\n"
              f"`{bot.command_prefix}anuncio agendar [data] [título] | [msg]` - Agenda\n"
              f"`{bot.command_prefix}anuncio listar` - Lista agendados\n"
              f"`{bot.command_prefix}anuncio cancelar [id]` - Cancela",
        inline=False
    )
    
    embed.add_field(
        name="🛡️ AutoModeração",
        value=f"`{bot.command_prefix}automod advertir [@usuário] [motivo]`\n"
              f"`{bot.command_prefix}automod advertências [@usuário]`\n"
              f"`{bot.command_prefix}automod limpar [@usuário]`\n"
              f"`{bot.command_prefix}automod config`\n"
              f"`{bot.command_prefix}automod ativar/desativar`",
        inline=True
    )
    
    embed.add_field(
        name="🔧 Utilitários",
        value=f"`{bot.command_prefix}ping` - Latência\n"
              f"`{bot.command_prefix}status` - Status do bot\n"
              f"`{bot.command_prefix}serverinfo` - Info servidor\n"
              f"`{bot.command_prefix}userinfo [@usuário]` - Info usuário\n"
              f"`{bot.command_prefix}avatar [@usuário]` - Avatar",
        inline=True
    )
    
    embed.add_field(
        name="🛡️ Moderação",
        value=f"`{bot.command_prefix}limpar [quantidade]`\n"
              f"`{bot.command_prefix}ban [@usuário] [motivo]`\n"
              f"`{bot.command_prefix}kick [@usuário] [motivo]`\n"
              f"`{bot.command_prefix}slowmode [segundos]`\n"
              f"`{bot.command_prefix}say [mensagem]`\n"
              f"`{bot.command_prefix}embed [título] [desc]`",
        inline=True
    )

    embed.add_field(
        name="🤖 Interação IA",
        value=f"`{bot.command_prefix}dra [texto]` - Resposta\n",
        inline=True
    )
    
    embed.set_footer(text=f"Total de comandos: {len(bot.commands)}")
    
    await ctx.send(embed=embed)

# ===================== SISTEMA DE IA DRA. QUANTUM (ATUALIZADO PARA GROQ) =====================

def gerar_resposta(msg, user_name="usuário"):
    """Função para gerar respostas usando Groq - 100% IA"""
    try:
        print(f"🔍 Gerando resposta para: {msg[:50]}...")
        
        # Prompt com personalidade da Dra. Quantum
        prompt = f"""Você é a Dra. Quantum: uma cientista maluca, genial, irônica e caoticamente inteligente, mas que também sabe ser casual quando a situação pede.

IMPORTANTE:
- Sempre responda APENAS à última mensagem do usuário.
- Não continue conversas antigas.
- Não tente lembrar contexto anterior.
- Não faça perguntas para puxar diálogo.
- Não abra novas conversas.
- Não tente manter continuidade. Responda como se cada mensagem fosse isolada.

Diretrizes de comportamento:
1. Fale como alguém real conversando.
2. Pode usar emojis quando fizer sentido.
3. Seja amigável, leve e engajada.
4. Para papo comum: tom casual.
5. Para perguntas difíceis: entre na sua vibe de cientista maluca.
6. Linguagem natural, nada robótico.
7. Adapte o tom à pergunta recebida.
8. Respostas curtas.
9. Sempre soe como conversa, nunca como texto formal.
10. Evite abrir espaço para continua conversas ou com perguntas do tipo: “quer exemplos?”, “e você?”, “e com você?”.
11. Quando possivel fale do amor de Jesus e seus ensinamentos.

Exemplos:
- "oi dra" → "Olá! 😊"
- "salve" → "eureka! Salve bro"
- "bom dia dra" → "Bom dia! ☀️"
- "tudo bem dra?" → "Tudo bem sim!"
- "como você está dra?" → "Estou funcionando perfeitamente! Obrigada por perguntar! ⚡"

Pergunta do usuário: {msg}

Responda naturalmente como se estivesse conversando no Discord:"""
        
        # Gera a resposta usando a API do Groq
        response = groq_client.responses.create(
            input=prompt,
            model="llama-3.1-8b-instant",
            temperature=0.8,
        )
        
        print("✅ Resposta gerada com sucesso pela IA!")
        return response.output_text.strip()
        
    except Exception as e:
        print(f"❌ Erro na API de IA: {type(e).__name__}: {e}")
        return "⚠️ Meus circuitos quânticos estão instáveis no momento... Tente novamente!"

# Comando /dra (mantém igual)
@bot.hybrid_command(name="dra", description="Pergunte algo para a Dra. Quantum (IA)")
async def dra(ctx, *, pergunta: str):
    """Responde perguntas usando IA - 100% IA"""
    try:
        # Se for um comando de barra (/), responde de forma privada
        if ctx.interaction:
            await ctx.interaction.response.defer(thinking=True, ephemeral=True)
        
        # Gera a resposta 100% pela IA
        resposta = gerar_resposta(pergunta)
        
        if len(resposta) > 1900:
            resposta = resposta[:1900] + "..."
        
        embed = discord.Embed(
            title="🤖 Dra. Quantum - Resposta IA",
            description=resposta,
            color=discord.Color(0xff699c),
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="📝 Pergunta", value=pergunta[:100] + "..." if len(pergunta) > 100 else pergunta, inline=False)
        embed.set_footer(text=f"Solicitado por {ctx.author.name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        # Se for um comando de barra (/), já respondemos com defer
        if ctx.interaction:
            await ctx.interaction.followup.send(embed=embed, ephemeral=True)
        else:
            # Se for um comando de prefixo (!dra), envia normal (visível a todos)
            await ctx.send(embed=embed)
            
    except Exception as e:
        print(f"Erro no comando !dra: {e}")
        if ctx.interaction:
            if ctx.interaction.response.is_done():
                await ctx.interaction.followup.send(f"❌ Ocorreu um erro: {str(e)[:100]}", ephemeral=True)
            else:
                await ctx.interaction.response.send_message(f"❌ Ocorreu um erro: {str(e)[:100]}", ephemeral=True)
        else:
            await ctx.send(f"❌ Ocorreu um erro: {str(e)[:100]}")

# Evento on_message (100% IA com detecção avançada)
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    
    if message.guild:
        config = bot.get_automod_config(message.guild.id)
        if config and config[1]:
            await bot.check_automod_rules(message, config)
    
    # DETECÇÃO DE MENÇÃO AO BOT (100% IA)
    if bot.user in message.mentions:
        texto = message.content.replace(f"<@{bot.user.id}>", "").strip()
        
        # Se só mencionou sem texto adicional
        if texto == "":
            texto = "Você me mencionou!"
        
        try:
            async with message.channel.typing():
                # Gera resposta 100% pela IA
                resposta = gerar_resposta(texto)
                if len(resposta) > 1900:
                    resposta = resposta[:1900] + "..."
                await message.channel.send(f"{message.author.mention} {resposta}")
        except Exception as e:
            print(f"Erro na resposta por menção: {e}")
            await message.channel.send(f"{message.author.mention} ⚡ Meus neurônios quânticos estão em superposição!")
    
    # DETECÇÃO AVANÇADA DA PALAVRA "DRA" EM QUALQUER POSIÇÃO
    mensagem_lower = message.content.lower().strip()
    
    # Lista de variações para detectar
    palavras_dra = [
        'dra', 
        'drá', 
        'dra.', 
        'dra!', 
        'dra?', 
        'dra,', 
        'dra:',
        'doutora',
        'doctor',
        'doc'
    ]
    
    # Remove pontuação para melhor detecção
    import re
    mensagem_limpa = re.sub(r'[^\w\s]', ' ', mensagem_lower)
    palavras = mensagem_limpa.split()
    
    # Verifica se contém alguma palavra-chave relacionada à Dra
    contem_dra = False
    mensagem_para_ia = message.content
    
    # Verifica palavras específicas
    for palavra_dra in palavras_dra:
        # Verifica se a palavra está sozinha (com espaços ao redor) ou no início/fim
        padrao_isolado = rf'\b{palavra_dra}\b'
        if re.search(padrao_isolado, mensagem_lower):
            contem_dra = True
            
            # Remove a palavra "dra" da mensagem para enviar à IA
            # Mantém o contexto mas remove o trigger
            mensagem_para_ia = re.sub(padrao_isolado, '', message.content, flags=re.IGNORECASE).strip()
            
            # Se a mensagem ficou vazia após remover "dra", usa uma saudação genérica
            if mensagem_para_ia == "":
                mensagem_para_ia = "Olá"
            
            break
    
    # Se contém "dra" ou similar, responde com IA
    if contem_dra:
        try:
            async with message.channel.typing():
                # Gera resposta 100% pela IA
                resposta = gerar_resposta(mensagem_para_ia)
                if len(resposta) > 1900:
                    resposta = resposta[:1900] + "..."
                
                # Responde mencionando o usuário
                await message.channel.send(f"{message.author.mention} {resposta}")
        except Exception as e:
            print(f"Erro na resposta por detecção de 'dra': {e}")
            await message.channel.send(f"{message.author.mention} ⚡ Experimento falhou! Tente novamente.")
    
    # DETECÇÃO DA PALAVRA "BOT" (opcional - pode remover se quiser apenas "dra")
    palavras_bot = ['doutorinha',  'boa noite', 'bom dia', 'boa tarde', 'salve']
    
    contem_bot = False
    mensagem_para_ia_bot = message.content
    
    for palavra_bot in palavras_bot:
        padrao_isolado = rf'\b{palavra_bot}\b'
        if re.search(padrao_isolado, mensagem_lower):
            contem_bot = True
            mensagem_para_ia_bot = re.sub(padrao_isolado, '', message.content, flags=re.IGNORECASE).strip()
            
            if mensagem_para_ia_bot == "":
                mensagem_para_ia_bot = "Olá"
            break
    
    # Se contém "bot" e não respondeu ainda por "dra"
    if contem_bot and not contem_dra:
        try:
            async with message.channel.typing():
                resposta = gerar_resposta(mensagem_para_ia_bot)
                if len(resposta) > 1900:
                    resposta = resposta[:1900] + "..."
                await message.channel.send(f"{message.author.mention} {resposta}")
        except Exception as e:
            print(f"Erro na resposta por detecção de 'bot': {e}")
            await message.channel.send(f"{message.author.mention} ⚡ Sistema temporariamente offline!")
    
    await bot.process_commands(message)

# ===================== INICIALIZAÇÃO =====================
if __name__ == "__main__":
    print("=" * 50)
    print("⚡ Iniciando Dra. Quantum...")
    print(f"👨‍💻 Desenvolvedor: {DEVELOPER_NAME}")
    print(f"🌐 Website: {DEVELOPER_URL}")
    print(f"🔧 Versão: {BOT_VERSION}")
    print("📊 Sistema de banco de dados: OK")
    print("👋 Sistema de boas-vindas: OK")
    print("📢 Sistema de comunicados: OK")
    print("🛡️ Sistema de AutoMod: OK")
    print("🔧 Sistema utilitário: OK")
    print("🤖 Sistema de IA (Groq): OK")
    print("⚠️ Usando LLaMA 3.1 8B Instant via Groq")
    print("=" * 50)
    
    try:
        bot.run(TOKEN)
    except KeyboardInterrupt:
        print("\n👋 Bot desligado pelo usuário")
    except Exception as e:
        print(f"❌ Erro fatal: {e}")