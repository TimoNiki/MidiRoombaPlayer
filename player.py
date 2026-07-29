import re
import sys
import serial
import argparse
from time import sleep

# Настройка аргументов
parser = argparse.ArgumentParser(description="Play music on Roomba.")
parser.add_argument('-p', '--port', default='/dev/ttyUSB0', help='Serial port')
parser.add_argument('-b', '--baud', default=115200, type=int, help='Baud rate')
parser.add_argument('-f', '--file', default=None, help='Path to song file (optional)')
parser.add_argument('--bpm', default=120, type=int, help='Beats per minute')
args = parser.parse_args()

out = []

# Источник данных: файл или консоль
input_source = open(args.file, 'r') if args.file else sys.stdin

if not args.file:
    print("Введите ноты: 'номер_ноты длительность'. Пустая строка — финиш.")

try:
    for line in input_source:
        line = line.strip()
        if not line:
            if out: break
            continue
        
        parts = re.split(r'\s+', line)
        if len(parts) < 2:
            print(f"⚠️ Пропущено (неверный формат): {line}")
            continue
            
        try:
            # Замена слова 'rest' или 'пауза' на код паузы для Roomba (обычно 30)
            note = 30 if parts[0].lower() in ['rest', 'пауза'] else int(parts[0])
            duration = int(parts[1])
            out.append([note, duration])
        except ValueError:
            print(f"⚠️ Ошибка в числах: {line}")
finally:
    if args.file:
        input_source.close()

if not out:
    print("❌ Нет данных для воспроизведения.")
    sys.exit()

# Работа с Roomba
try:
    with serial.Serial(args.port, args.baud, timeout=1) as ser:
        # Инициализация и перевод в режим Safe/Full
        ser.write(bytes([128, 131])) 
        sleep(0.2)
        
        noteno = 0
        songno = 0
        
        while noteno < len(out):
            remaining = len(out) - noteno
            chunk_size = min(remaining, 16) # Roomba принимает максимум 16 нот за раз
            
            # Команда 140: Запись песни (140, номер_песни, количество_нот)
            header = [140, songno, chunk_size]
            payload = []
            
            # Рассчет времени звучания пачки нот с учетом BPM
            # В Roomba длительность 64 = 1 секунда. Корректируем под BPM.
            time_factor = 60 / args.bpm / 16 
            total_duration_sec = 0
            
            for i in range(chunk_size):
                n = out[noteno + i]
                payload.extend([n[0], n[1]])
                total_duration_sec += (n[1] / 64.0) # Базовая длительность Roomba
            
            # Отправляем песню в память
            ser.write(bytes(header + payload))
            sleep(0.05)
            
            # Команда 141: Воспроизведение песни
            ser.write(bytes([141, songno]))
            print(f"🎵 Играет пачка нот. Песня слот: {songno}. Ждем {total_duration_sec:.2f} сек.")
            
            # Ждем, пока доиграет, чтобы не перегрузить буфер
            sleep(total_duration_sec + 0.1) 
            
            noteno += chunk_size
            songno = (songno + 1) % 4 # Цикл по слотам 0, 1, 2, 3

except serial.SerialException as e:
    print(f"❌ Ошибка подключения к Roomba: {e}")
