import discord
from discord.ext import commands, voice_recv
import asyncio
import logging
import discord.opus 
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

if not TOKEN:
    print("ERRO: Token não encontrado! Verifique o arquivo .env ou as variáveis de ambiente.")
    exit()

_original_decode = discord.opus.Decoder.decode

def safe_decode(self, data, fec=False):
    try:
        # Tenta decodificar normalmente
        return _original_decode(self, data, fec=fec)
    except discord.opus.OpusError:
        # Se der erro de "corrupted stream" (comum ao desconectar),
        # fingimos que recebemos um silêncio (bytes vazios) em vez de travar.
        # print("Debug: Erro de Opus prevenido com sucesso.")
        return bytes(0)

# 3. Substituímos a função na biblioteca
discord.opus.Decoder.decode = safe_decode
# -------------------------------------------

# Configuração de Logs (Silencia spams de RTCP)
logging.getLogger("discord.ext.voice_recv.reader").setLevel(logging.ERROR)
logging.getLogger("discord.ext.voice_recv.router").setLevel(logging.ERROR)

try:
    import audioop
except ImportError:
    try:
        import audioop_lts as audioop
    except ImportError:
        print("ERRO: Instale a lib de compatibilidade: pip install audioop-lts")
        exit()

# --- CONFIGURAÇÕES ---
LIMITE_VOLUME = 5000      # Ajuste conforme necessário
SENSIBILIDADE = 10        # Quantidade de pacotes seguidos para confirmar o grito

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

class DetectorDeGritos(voice_recv.AudioSink):
    def __init__(self, bot, channel_id):
        self.bot = bot
        self.channel_id = channel_id
        self.consecutive_loud_packets = {} 
        self.users_being_punished = set()

    def wants_opus(self):
        return False 

    def write(self, user, data):
        # Proteção: se o dado for vazio (nosso patch retornou bytes(0)), ignoramos
        if user is None or not data or not data.pcm: 
            return
        
        if user.id in self.users_being_punished: 
            return

        try:
            volume = audioop.rms(data.pcm, 2)
        except Exception:
            return

        # Lógica de Detecção
        if volume > LIMITE_VOLUME:
            current_count = self.consecutive_loud_packets.get(user.id, 0) + 1
            self.consecutive_loud_packets[user.id] = current_count
            
            if current_count >= SENSIBILIDADE:
                print(f"CONFIRMADO: {user.name} gritou (Vol: {volume}). Punindo...")
                self.users_being_punished.add(user.id)
                self.consecutive_loud_packets[user.id] = 0
                self.bot.loop.create_task(self.punir_usuario(user))
        else:
            if user.id in self.consecutive_loud_packets:
                self.consecutive_loud_packets[user.id] = 0

    async def punir_usuario(self, member):
        try:
            if member.voice:
                await member.move_to(None) # Desconecta o usuário
                
                channel = self.bot.get_channel(self.channel_id)
                if channel:
                    await channel.send(f"🔇 **{member.name}** foi brutalmente 👉👌")
        except discord.Forbidden:
            print(f"ERRO: Sem permissão para desconectar {member.name}.")
        except Exception as e:
            print(f"Erro ao punir: {e}")
        finally:
            # Espera 3 segundos para garantir que a desconexão terminou
            await asyncio.sleep(3)
            if member.id in self.users_being_punished:
                self.users_being_punished.remove(member.id)

    def cleanup(self):
        pass

@bot.event
async def on_ready():
    print(f'Bot iniciado como {bot.user}')
    print('Vacina Opus aplicada. Aguardando comando !cassar')

@bot.command()
async def cassar(ctx):
    if not ctx.author.voice:
        return await ctx.send("Entre em um canal de voz primeiro!")

    voice_channel = ctx.author.voice.channel
    
    try:
        if ctx.voice_client:
            await ctx.voice_client.disconnect()
            await asyncio.sleep(1)

        vc = await voice_channel.connect(cls=voice_recv.VoiceRecvClient)
        vc.listen(DetectorDeGritos(bot, ctx.channel.id))
        await ctx.send(f"👿 Vigiar ativado em **{voice_channel.name}**.")
    except Exception as e:
        await ctx.send(f"Erro ao conectar: {e}")

@bot.command()
async def sair(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Monitoramento encerrado.")
    else:
        await ctx.send("Não estou conectado.")

bot.run(TOKEN)