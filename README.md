# MayoraGameSuit (Fortune Hands)

MayoraGameSuit adalah game suit batu gunting kertas yang memakai kamera dan MediaPipe.
Aplikasi berjalan sebagai server lokal berbasis Flask dan dibuka melalui browser.

## Fitur
- Deteksi tangan dan gesture rock/paper/scissors.
- Tampilan game berbasis web (HTML/CSS/JS).
- Audio dan animasi.
- Dukungan opsional Arduino/ESP32 untuk servo (endpoint /api/servo/collect).

## Menjalankan EXE
1. Jalankan `MayoraGameSuit.exe`.
2. Jika browser tidak otomatis terbuka, buka `http://127.0.0.1:5000/`.
3. Izinkan akses kamera dan firewall jika diminta.

## Menjalankan dari Source
```
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\python.exe app.py
```

## Build
- Onedir (lebih stabil):
```
.venv\Scripts\pyinstaller.exe --onedir --name MayoraGameSuit --console --add-data "templates;templates" --add-data "static;static" --collect-data mediapipe --collect-submodules mediapipe app.py
```
- Onefile (lebih praktis, startup lebih lambat):
```
.venv\Scripts\pyinstaller.exe --onefile --name MayoraGameSuit --console --add-data "templates;templates" --add-data "static;static" --collect-data mediapipe --collect-submodules mediapipe app.py
```

## Troubleshooting
- Kamera tidak terdeteksi: pastikan tidak dipakai aplikasi lain.
- Layar kosong: tunggu server start; lihat console.
- Onefile gagal jalan: gunakan onedir.

## Download
- Link: https://drive.google.com/file/d/183N_KAxS_9mo7iutN9lerHFfrAJESYPf/view?usp=sharing
- Jika diunduh lewat script otomatis, file akan tersimpan di folder `downloads`.

## Download 2
- Link: [https://drive.google.com/file/d/183N_KAxS_9mo7iutN9lerHFfrAJESYPf/view?usp=sharing](https://drive.google.com/file/d/1OnJDvB37xAUizqgkQTemfedDsNYksU3O/view?usp=sharing)
- Jika diunduh lewat script otomatis, file akan tersimpan di folder `downloads`.
