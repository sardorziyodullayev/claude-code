# Promo video (Reels)

Kod bilan yasalgan vertikal motion-reklama: 1080×1920, 30 fps, 15 s, 128 BPM ritmda tez montaj.

- `reel.mp4` — Instagram Reels uchun: qora fon, tepada matn, o'rtada reklama.
- `ad.mp4` — reklamaning o'zi, toza holda.
- `make_ad.py` — ikkala videoni qayta yasaydigan skript (rasmlar ham, musiqa ham kod bilan yaratiladi).

## Qayta yasash

```bash
pip install pycairo numpy
python3 make_ad.py <chiqish_papkasi>   # ffmpeg kerak
```

Matnlar, ranglar va brend nomi skript boshidagi `CONFIG` bo'limida; kadrlar ketma-ketligi va davomiyligi `TIMELINE` ro'yxatida (sakkizlik notalarda).
