import serial
from pathlib import Path
from PIL import Image
import time
import importlib

# --- fix beállítások ---
PORT = "COM3"
BAUD = 500000
W, H = 320, 240
OUT = "frame.png"

START_COMMAND = 0x00
COMMAND_MASK = 0x0F
COMMAND_DEBUG_DATA = 0x03

# --- led art ---
def send_led(ser: serial.Serial, rows8):
    pkt = bytes([0x7E, ord('L')]) + bytes(rows8[:8])
    ser.write(pkt)

ICON_SMILE = [
    0b00111100,
    0b01000010,
    0b10100101,
    0b10000001,
    0b10100101,
    0b10011001,
    0b01000010,
    0b00111100,
]

ICON_APPLE = [
    0b00010000,
    0b00011000,
    0b00001000,
    0b00110110,
    0b01111111,
    0b01111111,
    0b01111111,
    0b00110110,
]
ICON_BANANA = [
    0b01000000,
    0b11000000,
    0b11000000,
    0b11100000,
    0b11110001,
    0b01111111,
    0b00111110,
    0b00001100,
]

ICON_QUESTIONMARK = [
    0b00011000,
    0b00100100,
    0b00100100,
    0b00001000,
    0b00010000,
    0b00010000,
    0b00000000,
    0b00010000,
]

# --- segéd fgvk ---

def rgb565_to_rgb888(hb: int, lb: int):
    raw = ((hb & 0xFF) << 8) | (lb & 0xFF)
    r = (raw >> 8) & 0xF8
    g = (raw >> 3) & 0xFC
    b = (raw << 3) & 0xF8
    return (r, g, b)

def wait_for_vsync(ser: serial.Serial):
    in_cmd = False
    cmd_len = -1
    cmd_buf = bytearray()
    while True:
        b = ser.read(1)
        if not b:
            continue
        x = b[0]
        if not in_cmd and x == START_COMMAND:
            in_cmd = True
            cmd_len = -1
            cmd_buf.clear()
            continue
        if in_cmd:
            if cmd_len < 0:
                cmd_len = x & 0xFF
            else:
                cmd_buf.append(x)
                if len(cmd_buf) >= cmd_len + 1:
                    checksum = 0
                    for i in range(cmd_len):
                        checksum ^= cmd_buf[i]
                    ok = (checksum == cmd_buf[cmd_len])
                    if ok and cmd_len > 0:
                        payload = bytes(cmd_buf[:cmd_len])
                        code = payload[0] & COMMAND_MASK
                        if code == COMMAND_DEBUG_DATA:
                            try:
                                txt = payload[1:].decode(errors="replace")
                            except Exception:
                                txt = ""
                            if "vsync" in txt.lower():                             
                                print("[DEBUG] Vsync")
                                return
                    in_cmd = False
                    cmd_len = -1
                    cmd_buf.clear()
            continue

def capture_one_frame_after_vsync(ser: serial.Serial):
    
    total_pixels = W * H
    pixels = []
    half = None
    print("[INFO] Képcapture indul…")
    while len(pixels) < total_pixels:
        b = ser.read(1)
        if not b:
            continue
        x = b[0]
        if half is None:
            half = x
        else:
            hb, lb = half, x
            pixels.append(rgb565_to_rgb888(hb, lb))
            half = None
    return pixels

def run_diagnose(image_path: Path) -> str:
    """
    Meghívja a diagnose.py -> diagnose(image_path) függvényt.
    A visszatérési érték string pl. 'APPLE' vagy 'BANANA'.
    """
    try:
        diag = importlib.import_module("diagnose")
        res = diag.diagnose(str(image_path))
        key = str(res).strip().upper()
        if key in ("APPLE", "ALMA"):
            return "APPLE"
        elif key in ("BANANA", "BANÁN", "BANAN"):
            return "BANANA"
        else:
            return "UNKNOWN"
    except Exception as e:
        print(f"[WARN] diagnose hiba vagy hiányzik: {e}")
        return "UNKNOWN"

def main():
    with serial.Serial(PORT, BAUD, timeout=0.05) as ser:
        print(f"[INFO] Várakozás Vsync-re ({PORT} @ {BAUD})…")      

        wait_for_vsync(ser)
        pixels = capture_one_frame_after_vsync(ser)

        im = Image.new("RGB", (W, H))
        im.putdata(pixels[:W*H])
        out_path = Path(OUT).resolve()
        im.save(out_path)
        print(f"[OK] Mentve (teljes kép): {out_path} ({W}x{H})")

        # diagnosztika meghívása
        verdict = run_diagnose(out_path)
        print(f"[INFO] diagnose eredmény: {verdict}")

        # ikon választás
        if verdict == "APPLE":
            send_led(ser, ICON_APPLE)
        elif verdict == "BANANA":
            send_led(ser, ICON_BANANA)
        else:
            send_led(ser, ICON_SMILE)

        time.sleep(3)
        send_led(ser, ICON_SMILE)

if __name__ == "__main__":
    main()
