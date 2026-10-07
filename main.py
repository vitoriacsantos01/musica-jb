import time
import sys
import os
import threading
import random

# --- CONSTANTES ANSI (Cores e Comandos para o Terminal) ---
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
# MODIFICAÇÃO: Cor para INFO (Título/Artista) e para a Névoa (roxo claro)
INFO_COLOR = "\033[38;5;140m"   # roxo /boldo
ACTIVE_LYRIC_COLOR = "\033[38;5;183m"
INACTIVE_LYRIC_COLOR = "\033[38;5;245m"

# MODIFICAÇÃO: Cores para a NÉVOA (tons de roxo e rosa)
NEBULA_COLORS = [
    "\033[38;5;236m", # cinza escuro
    "\033[38;5;238m", # Outro cinza escuro
    "\033[38;5;218m", # rosa 
    "\033[38;5;140m",  # roxo claro/boldo (o mesmo do INFO_COLOR)
    "\033[38;5;146m",  # um roxo um pouco mais claro/sutil para variação na névoa
] 
NEBULA_CHAR = "•"

# --- FUNÇÕES ANSI ---
CURSOR_POS = lambda row, col: f"\033[{row};{col}H"
CLEAR_SCREEN = "\033[H\033[J"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"

# --- VARIÁVEIS GLOBAIS ---
terminal_width = 80
terminal_height = 24

# Configurações da caixa de lyrics
BOX_WIDTH = 60
BOX_HEIGHT = 12

# Posição da caixa no terminal
BOX_START_COL = 5
BOX_START_ROW = (terminal_height - BOX_HEIGHT) // 2 - 2

# Variáveis da Névoa
NEBULA_DENSITY = 0.003
NEBULA_UPDATE_INTERVAL = 0.1
NEBULA_PULSE_DURATION = 0.6

NEBULA_AREA_PADDING_HORIZONTAL = 0
NEBULA_AREA_PADDING_VERTICAL = 0

stop_nebula_animation = False
nebula_thread = None
screen_lock = threading.Lock()

active_nebula_pixels = {}

# --- FUNÇÃO PARA AJUSTAR O TEXTO À LARGURA DA CAIXA ---
def wrap_text_to_lines(text, max_width):
    if not text:
        return [""]
    words = text.split()
    wrapped_lines = []
    current_line = []
    current_line_length = 0

    for word in words:
        # Lida com palavras individuais que são maiores que a largura máxima
        if len(word) > max_width:
            if current_line: # Se já houver algo na linha atual, adicione-o antes
                wrapped_lines.append(" ".join(current_line))
            wrapped_lines.append(word) # Adiciona a palavra longa sozinha
            current_line = []
            current_line_length = 0
            continue

        # Verifica se adicionar a próxima palavra excede o limite
        # Adiciona 1 para o espaço entre as palavras
        if current_line_length + len(word) + (1 if current_line else 0) <= max_width:
            current_line.append(word)
            current_line_length += len(word) + (1 if current_line else 0)
        else:
            wrapped_lines.append(" ".join(current_line))
            current_line = [word]
            current_line_length = len(word)
            
    if current_line:
        wrapped_lines.append(" ".join(current_line))
    return wrapped_lines

# --- FUNÇÃO PARA EXIBIR A TELA INICIAL ---
def display_initial_setup_screen():
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.write(f"{CURSOR_POS(1, 2)}{BOLD}{INFO_COLOR}[SYSTEM]{RESET} Inicializando módulos para Spotify Layout...\n")
    sys.stdout.write(f"{CURSOR_POS(2, 2)}{INFO_COLOR}[STATUS]{RESET} Preparando exibição das lyrics...\n")
    sys.stdout.write(f"{CURSOR_POS(3, 2)}{INFO_COLOR}[STATUS]{RESET} Ajustando parâmetros de névoa para imersão total...\n")
    sys.stdout.flush()
    time.sleep(2.0)
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.flush()

# --- FUNÇÃO DA ANIMAÇÃO DA NÉVOA DE FUNDO ---
def animate_nebula_background():
    while not stop_nebula_animation:
        current_time = time.monotonic()
        pixels_to_remove = []

        with screen_lock:
            neb_start_row_0based = 0
            neb_start_col_0based = 0
            neb_end_row_0based = terminal_height - 1
            neb_end_col_0based = terminal_width - 1
            nebula_area_width = max(0, terminal_width)
            nebula_area_height = max(0, terminal_height)

            for pos, pixel_info in list(active_nebula_pixels.items()):
                row_0based, col_0based, timestamp, original_char = pixel_info
                if current_time - timestamp > NEBULA_PULSE_DURATION:
                    sys.stdout.write(CURSOR_POS(row_0based + 1, col_0based + 1) + original_char)
                    pixels_to_remove.append(pos)
            
            for pos in pixels_to_remove:
                del active_nebula_pixels[pos]

            if nebula_area_width > 0 and nebula_area_height > 0:
                new_pixels_count = int(nebula_area_width * nebula_area_height * NEBULA_DENSITY)
            else:
                new_pixels_count = 0

            for _ in range(new_pixels_count):
                row_0based = random.randint(neb_start_row_0based, neb_end_row_0based)
                col_0based = random.randint(neb_start_col_0based, neb_end_col_0based)
                
                row_1based = row_0based + 1
                col_1based = col_0based + 1

                is_within_lyrics_box = (
                    row_1based >= BOX_START_ROW and row_1based < BOX_START_ROW + BOX_HEIGHT and
                    col_1based >= BOX_START_COL and col_1based < BOX_START_COL + BOX_WIDTH
                )
                
                if not is_within_lyrics_box:
                    original_char_at_pos = " " 
                    
                    color_char = random.choice(NEBULA_COLORS) + NEBULA_CHAR + RESET
                    sys.stdout.write(CURSOR_POS(row_1based, col_1based) + color_char)
                    
                    active_nebula_pixels[(row_0based, col_0based)] = (row_0based, col_0based, current_time, original_char_at_pos)
            sys.stdout.flush()
        
        time.sleep(NEBULA_UPDATE_INTERVAL)


# --- FUNÇÃO PRINCIPAL: Display das Lyrics no Estilo Spotify ---
def display_spotify_lyrics(current_line_index, lyrics_data, music_info):
    global terminal_width, terminal_height, BOX_WIDTH, BOX_HEIGHT, BOX_START_ROW, BOX_START_COL
    
    with screen_lock:
        try:
            current_term_width, current_term_height = os.get_terminal_size()
            terminal_width = max(80, current_term_width)
            terminal_height = max(24, current_term_height)
            
            BOX_START_ROW = (terminal_height - BOX_HEIGHT) // 2 - 2
            BOX_START_COL = 5
        except OSError:
            pass

        for r in range(BOX_HEIGHT):
            sys.stdout.write(CURSOR_POS(BOX_START_ROW + r + 1, BOX_START_COL + 1) + " " * BOX_WIDTH)

        current_display_row = 0

        # --- Exibe Título da Música DENTRO DA CAIXA (AGORA EM VERDE MUSGO/BOLDO) ---
        title_line = music_info["title"]
        title_wrapped = wrap_text_to_lines(title_line, BOX_WIDTH - 4) # Título ainda usa largura da caixa
        for line in title_wrapped:
            if current_display_row < BOX_HEIGHT:
                sys.stdout.write(CURSOR_POS(BOX_START_ROW + current_display_row + 1, BOX_START_COL + 2))
                sys.stdout.write(f"{BOLD}{INFO_COLOR}{line}{RESET}")
                current_display_row += 1
        
        # --- Exibe Artista DENTRO DA CAIXA (AGORA EM VERDE MUSGO/BOLDO) ---
        artist_line = music_info["artist"]
        artist_wrapped = wrap_text_to_lines(artist_line, BOX_WIDTH - 4) # Artista ainda usa largura da caixa
        for line in artist_wrapped:
            if current_display_row < BOX_HEIGHT:
                sys.stdout.write(CURSOR_POS(BOX_START_ROW + current_display_row + 1, BOX_START_COL + 2))
                sys.stdout.write(f"{INFO_COLOR}{line}{RESET}")
                current_display_row += 1
        
        if current_display_row < BOX_HEIGHT:
            current_display_row += 1

        # --- Prepara e exibe as linhas de lyrics (dentro da caixa central) ---
        lyrics_lines_to_show = []
        
        # Definindo uma largura de quebra mais restritiva para as letras
        LYRIC_WRAP_WIDTH = BOX_WIDTH // 2 # Isso vai forçar linhas mais curtas (aprox. 30 caracteres)

        for i in range(current_line_index - 2, current_line_index):
            if i >= 0:
                lyrics_lines_to_show.append({"text": lyrics_data[i]["original"], "color": DIM + INACTIVE_LYRIC_COLOR})
            else:
                lyrics_lines_to_show.append({"text": "", "color": ""})

        if current_line_index < len(lyrics_data):
            lyrics_lines_to_show.append({"text": lyrics_data[current_line_index]["original"], "color": BOLD + ACTIVE_LYRIC_COLOR})
        else:
            lyrics_lines_to_show.append({"text": "", "color": ""})

        lyrics_rows_remaining = BOX_HEIGHT - current_display_row
        for i in range(current_line_index + 1, current_line_index + 1 + lyrics_rows_remaining):
            if i < len(lyrics_data):
                lyrics_lines_to_show.append({"text": lyrics_data[i]["original"], "color": DIM + INACTIVE_LYRIC_COLOR})
            else:
                lyrics_lines_to_show.append({"text": "", "color": ""})

        for line_data in lyrics_lines_to_show:
            # AQUI é onde mudamos a largura para as letras
            wrapped_lines = wrap_text_to_lines(line_data["text"], LYRIC_WRAP_WIDTH) 
            for wrapped_line in wrapped_lines:
                if current_display_row < BOX_HEIGHT:
                    current_col_pos = BOX_START_COL + 2
                    sys.stdout.write(CURSOR_POS(BOX_START_ROW + current_display_row + 1, current_col_pos))
                    sys.stdout.write(f"{line_data['color']}{wrapped_line}{RESET}")
                    current_display_row += 1
                else:
                    break
            if current_display_row >= BOX_HEIGHT:
                break
        
        sys.stdout.flush()


# --- FUNÇÃO PARA LIMPAR TODOS OS PIXELS DE NÉVOA VISÍVEIS ---
def clear_all_nebula_pixels():
    with screen_lock:
        for row_0based, col_0based, _, original_char in active_nebula_pixels.values():
            sys.stdout.write(CURSOR_POS(row_0based + 1, col_0based + 1) + original_char)
        active_nebula_pixels.clear()
        sys.stdout.flush()

# --- DADOS DA MÚSICA ---
MUSIC_INFO = {
    "title": "Hard 2 Face Reality",
    "artist": "Justin Bieber"
}

LYRICS_DATA = [
    {"time": 0.0, "original": "Don’t be afraid to stand alone"},
    {"time": 4.0, "original": "Don’t be afraid to stand outside the comfort zone"},
    {"time": 8.0, "original": "I know it’s hard away from home"},
    {"time": 12.0, "original": "And it ain’t easy all alone"},
    {"time": 16.0, "original": "Relationships over the phone"},
    {"time": 20.0, "original": "Talkin’ to your significant other all night long"},
    {"time": 24.0, "original": "Sometimes it’s hard to face reality, oh, oh"},
    {"time": 28.0, "original": "--- 💜 ---", "type": "end_of_song"}
]

TOTAL_MUSIC_DURATION = 50.0 # Ajustado para acomodar as lyrics até o fim e a mensagem de "fim da música"

# --- FUNÇÃO PRINCIPAL PARA A ANIMAÇÃO ---
def start_lyrics_animation():
    global stop_nebula_animation, nebula_thread

    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.write(CLEAR_SCREEN)
    sys.stdout.flush()

    stop_nebula_animation = False
    nebula_thread = threading.Thread(target=animate_nebula_background)
    nebula_thread.daemon = True
    nebula_thread.start()

    start_time = time.monotonic()
    current_line_index = 0
    
    while time.monotonic() - start_time < TOTAL_MUSIC_DURATION:
        elapsed_time = time.monotonic() - start_time
        
        try:
            current_term_width, current_term_height = os.get_terminal_size()
            global terminal_width, terminal_height, BOX_START_ROW, BOX_START_COL
            terminal_width = max(80, current_term_width)
            terminal_height = max(24, current_term_height)
            BOX_START_ROW = (terminal_height - BOX_HEIGHT) // 2 - 2
            BOX_START_COL = 5
        except OSError:
            pass

        if current_line_index < len(LYRICS_DATA):
            next_line_data = LYRICS_DATA[current_line_index]
            
            if elapsed_time >= next_line_data["time"]:
                display_spotify_lyrics(current_line_index, LYRICS_DATA, MUSIC_INFO)
                
                if next_line_data.get("type") == "end_of_song":
                    pass 
                
                current_line_index += 1 
            else:
                time.sleep(min(0.1, next_line_data["time"] - elapsed_time))
        else:
            display_spotify_lyrics(current_line_index - 1, LYRICS_DATA, MUSIC_INFO)
            time.sleep(0.1)
        
    stop_nebula_animation = True 
    if nebula_thread and nebula_thread.is_alive():
        nebula_thread.join(timeout=1)

    clear_all_nebula_pixels()

    with screen_lock:
        sys.stdout.write(CLEAR_SCREEN)
        
        final_message = "MÚSICA ENCERRADA"
        final_message_col = (terminal_width - len(final_message) - len(BOLD) - len(INFO_COLOR) - len(RESET)) // 2
        final_message_row = terminal_height // 2
        
        sys.stdout.write(f"{CURSOR_POS(final_message_row, final_message_col)}{BOLD}{INFO_COLOR}{final_message}{RESET}\n")
        sys.stdout.write(f"{CURSOR_POS(final_message_row + 1, (terminal_width - len('Obrigado por ouvir!') - len(INFO_COLOR) - len(RESET)) // 2)}{INFO_COLOR}Obrigado por ouvir!{RESET}\n")
        sys.stdout.flush()
    
    time.sleep(3)

# --- Ponto de Entrada do Programa ---
if __name__ == "__main__":
    try:
        display_initial_setup_screen()
        start_lyrics_animation()
        
        with screen_lock:
            sys.stdout.write(CLEAR_SCREEN)
            sys.stdout.write(CURSOR_POS(terminal_height // 2 - 1, (terminal_width - len("Programa finalizado. Pressione Enter para sair.")) // 2))
            sys.stdout.write("Programa finalizado. Pressione Enter para sair.\n")
            sys.stdout.flush()
        
        input()
    except KeyboardInterrupt:
        print("\nExibição interrompida pelo usuário.")
    except Exception as e:
        print(f"\nOcorreu um erro: {e}")
    finally:
        stop_nebula_animation = True
        if nebula_thread and nebula_thread.is_alive():
            nebula_thread.join(timeout=1)
        clear_all_nebula_pixels()
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()