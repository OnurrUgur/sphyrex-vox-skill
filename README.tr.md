# sphyrex-vox-skill

**Vox tarzı editoryal kâğıt kolajı ve gravür haritalı mini-belgeseller (9:16 Shorts/Reels ve 16:9 YouTube) üreten açık kaynak Ajan Skill'i (Claude Code · OpenAI Codex · Google Antigravity) ve deterministik Python motoru (`vox_kit`).**

[English README →](README.md) · [Skill Kuralları (`SKILL.md`)](SKILL.md) · [Ajan Yönergesi (`AGENTS.md`)](AGENTS.md)

> **Sorumluluk Reddi:** Bu yazılım herhangi bir garanti olmaksızın "olduğu gibi" sunulur. Videolarda kullandığınız veri ve rakamların doğruluğu, eklediğiniz üçüncü taraf medyaların telif/lisans uygunluğu ve platform kurallarına uyum tamamen kullanıcının sorumluluğundadır. Sphyrex herhangi bir sunucu/bulut hizmeti sağlamaz ve kullanıcı verisi toplamaz. "Sphyrex" marka adı ve maskot görselleri MIT lisansı kapsamı dışındadır.

---

## Neden Hibrit (%75 Kod + %25 Opsiyonel AI)?

Videoyu tamamen yapay zekâ video araçlarına bırakmak 3 büyük sorun çıkarır: Türkçe yazılar bozulur, ülke sınırları uydurulur ve 24 FPS klipler 30 FPS zaman çizelgesinde takılır. After Effects ile elle yapmak ise dakika başına günler sürer.

`sphyrex-vox-skill` işi ikiye ayırır:
- **Deterministik Python Motoru (`vox_kit` — %70–80, $0 API maliyeti):** Natural Earth `1:50m` gerçek gravür dünya haritası ve 3 seviyeli mipmap kamera, organik yırtık kâğıt kartları, harflere asla binmeyen dış köşe maskeleme bandı, yırtık belge üstü aşınmış kırmızı mühürler, alttan yatay yırtık siyah kontrast perdesi, animasyonlu kırılım grafikleri, 9 prosedürel halftone gravür ikon, Whisper kelime-anlam senkronlu sıfır titremeli altyazı (`<=17` karakter tek satır), saf NumPy organik SFX ve iki geçişli `-14 LUFS` ses seviyesi.
- **Opsiyonel Sıfır Metinli AI Kahraman Klipleri (%20–30, 24 FPS):** İsterseniz `references/FLOW-PROMPTS.md` şablonlarıyla Google Flow / Veo vb. araçtan 2–4 adet kısa (2–3 sn) yazısız kolaj klibi üretip sözün anlamına göre zaman çizelgesine takabilirsiniz.

---

## Gereksinimler

- **Python 3.9+** (`python3 --version`)
- **`PATH` içinde `ffmpeg` ve `ffprobe`**
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`
  - Windows: `winget install Gyan.FFmpeg`
- Python paketleri (`Pillow`, `numpy`) — `pip install -e .` ile otomatik kurulur.

---

## Adım 1 · Motoru Kurun

```bash
git clone https://github.com/OnurrUgur/sphyrex-vox-skill.git
cd sphyrex-vox-skill
pip install -e .
```

Kurulumu ~1 saniyede doğrulayın (12 birim, güvenlik ve uçtan uca render testi):

```bash
python3 -m unittest discover -s tests -v
```

---

## Adım 2 · Skill'i Ajanınıza Bağlayın

`sphyrex-vox-skill`, standart `SKILL.md` + `AGENTS.md` yapısıyla **Claude Code**, **OpenAI Codex CLI** ve **Google Antigravity** ile doğrudan uyumludur. Klonladığınız `sphyrex-vox-skill` klasörünün içinde kullandığınız araca göre ilgili komutu çalıştırın:

### Claude Code
```bash
mkdir -p ~/.claude/skills
ln -s "$(pwd)" ~/.claude/skills/sphyrex-vox-skill
```

### OpenAI Codex CLI
```bash
mkdir -p ~/.codex/skills
ln -s "$(pwd)" ~/.codex/skills/sphyrex-vox-skill
```
*(İsterseniz proje içi `.agents/skills/sphyrex-vox-skill` altına da bağlayabilirsiniz; repo içinde çalıştırıldığında `AGENTS.md` otomatik okunur.)*

### Google Antigravity (`agy` / IDE)
```bash
mkdir -p ~/.agents/skills
ln -s "$(pwd)" ~/.agents/skills/sphyrex-vox-skill
```
*(Antigravity CLI ve IDE genelinde `~/.agents/skills/` altından otomatik tanınır.)*

> **Windows (PowerShell):** `ln -s` yerine klasörü doğrudan `%USERPROFILE%\.claude\skills\sphyrex-vox-skill`, `%USERPROFILE%\.codex\skills\sphyrex-vox-skill` veya `%USERPROFILE%\.agents\skills\sphyrex-vox-skill` içine kopyalayabilirsiniz.

---

## Adım 3 · Hazır 48 sn Demoyu Basın veya Ajanınıza Tek Cümle Verin

### Seçenek A — Hazır 48 Saniyelik Mini-Belgesel Demosu
*"180 TL'lik bir kahveden çiftçiye ne kalıyor?"* (9:16 dikey, 24 FPS, saf kod, $0 API maliyeti):

```bash
python3 -m vox_kit map-prep --countries BRA,COL,TUR --out examples/kahve_180tl/cache/map
python3 -m vox_kit render examples/kahve_180tl/scene.py --out examples/kahve_180tl/out/kahve-demo.mp4
python3 -m vox_kit check examples/kahve_180tl/out/kahve-demo.mp4
python3 -m vox_kit contact-sheet examples/kahve_180tl/out/kahve-demo.mp4 --out examples/kahve_180tl/out/sheets
```

**16:9 YouTube yatay** çıktı için `render` komutuna `--aspect 16:9` eklemeniz yeterlidir.

### Seçenek B — Kendi Konunuzu Tek Cümleyle Ürettirin
**Claude Code**, **Codex** veya **Antigravity**'yi açıp şunu yapıştırın:

> *"`sphyrex-vox-skill` kullanarak [konun] hakkında 45 saniyelik 9:16 Vox tarzı mini-belgesel üret. Önce rakamları gerçek kaynaklardan doğrula, Natural Earth harita önbelleğini kur, 24 FPS bas ve bana göstermeden önce `vox_kit check` + `contact-sheet` çalıştır."*

Sıfırdan yeni sahne şablonu açmak için:
```bash
python3 -m vox_kit init ./benim-belgeselim
```

---

## Güvenlik ve Gizlilik

- **Yerel çalışma:** Telemetri ve zorunlu API anahtarı olmadan kendi bilgisayarınızda çevrimdışı çalışacak şekilde tasarlanmıştır.
- **Yalnız güvendiğiniz sahne dosyalarını çalıştırın:** `python3 -m vox_kit render <sahne.py>` hedef Python sahne dosyasını doğrudan çalıştırır — yalnızca kendinizin yazdığı veya güvendiğiniz `.py` sahnelerini çalıştırın.
- **Sertleştirilmiş dosya yolları ve ffmpeg girişleri:** Harita önbelleği yol kaçışını (`..`) ve mutlak yolları reddeder; tüm medya yolları kanonik mutlak yola çözülür, loudnorm ölçümleri sonlu sayı olarak doğrulanır ve tüm alt süreç çağrıları kabuk yorumlayıcısı olmadan açık argüman listeleriyle çalışır.

## Lisans

Kod MIT lisansı altındadır (`LICENSE`). Natural Earth 1:50m harita verisi Kamu Malıdır (Public Domain). Paket içi fontlar (Anton, Sora, Cinzel) SIL OFL 1.1 lisanslıdır.
