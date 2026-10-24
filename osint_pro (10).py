#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-PRO v6.5 MONTANA/FSOCIETY | Online Hesap + Yasal / Pasif OSINT Aracı (GitHub + Termux uyumlu)
=====================================================
Kategoriler:
  1) Kullanıcı adı araştırma
  2) E-posta araştırma
  3) Domain / site analizi
  4) IP araştırma
  5) Güvenlik ve teknoloji kontrolleri
  6) İnternet ve sosyal platform arama bağlantıları
  7) Ek araçlar (RDAP, Wayback, hash tanıma, Discord)

Erişim: genel giriş şifresi YOK, doğrudan kategori seçilir. NORMAL her zaman
şifresizdir; VIP/DOST/ADMIN kendi kategori şifresini ister (ilk kurulumda siz belirlersiniz).
İlk çalıştırmada hazır şifreler yüklenir (~/.osint_pro/ayar.json, hash'li); kendi şifreniz için:
OSINT_KURULUM=1 python osint_pro.py  ya da Admin Paneli > Şifreleri değiştir.
Sadece herkese açık kaynakları kullanır. Port tarama, sızma, brute-force,
hash kırma, token/hesap erişimi YOKTUR. Sadece standart Python kütüphanesi.

Online hesap sunucusu (HTTPS reverse proxy arkasında yayınlayın):
    python osint_pro_montana_fsociety.py --auth-server
İstemci: OSINT_AUTH_URL=https://auth.example.com python osint_pro_montana_fsociety.py

GitHub'dan indirip çalıştırma (Termux / Linux / macOS):
    pkg install git python -y        (Termux)     |  apt install git python3 -y   (Linux)
    git clone https://github.com/<kullanici-adiniz>/<repo-adi>.git
    cd <repo-adi>
    python osint_pro.py

Güncelleme (depoyu yeniden çekmeden):
    cd <repo-adi> && git pull && python osint_pro.py

Kurulum (sadece Termux, dosyayı elle attıysanız):
    pkg update && pkg install python -y
    python osint_pro.py

Hızlı kullanım:
    python osint_pro.py -d example.com     tam domain raporu
    python osint_pro.py -u kullaniciadi    kullanıcı adı kontrolü
    python osint_pro.py -e ornek@mail.com  e-posta araştırma
    python osint_pro.py -i 8.8.8.8         IP araştırma

Renkleri kapatmak için: NO_COLOR=1 python osint_pro.py
Animasyonları kapatmak için: OSINT_NOANIM=1 python osint_pro.py
Açılış görselini kapatmak için: OSINT_NOSPLASH=1 python osint_pro.py
Raporlar: ~/osint_raporlari/

UYARI: Yalnızca izinli hedeflerde ve yürürlükteki yasalara (KVKK dahil) uygun
şekilde kullanın. Sonuçlar kesin kimlik doğrulaması değildir.
"""

import base64
import concurrent.futures as cf
import datetime
import getpass
import hashlib
import hmac
import ipaddress
import json
import math
import os
import random
import re
import shutil
import socket
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib

# ============================================================ AYARLAR
UA = {"User-Agent": "Mozilla/5.0 (Linux; Android 13) OSINT-PRO/2.0 (educational)"}
TIMEOUT = 20
THREADS = 20
RAPOR_DIZINI = os.path.join(os.path.expanduser("~"), "osint_raporlari")

# ============================================================ RENKLER
RENK = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
ANIM = RENK and not os.environ.get("OSINT_NOANIM")  # animasyonları kapatmak için OSINT_NOANIM=1


def _c(n):
    return f"\033[38;5;{n}m" if RENK else ""


X = "\033[0m" if RENK else ""
BOLD = "\033[1m" if RENK else ""
KIRMIZI, YESIL, SARI, MAVI = _c(196), _c(46), _c(220), _c(39)
CYAN, MOR, BEYAZ, GRI = _c(51), _c(129), _c(255), _c(244)
TURUNCU, PEMBE = _c(208), _c(213)

ANSI = re.compile(r"\033\[[0-9;]*m")
RAPOR = []


# ---- animasyon altyapısı: tek bir döngü dönen yükleniyor göstergesi
_KILIT = threading.Lock()
_SP = {"mesaj": "", "toplam": 0, "sayi": 0, "calisiyor": False, "pause": False,
       "stack": [], "t0": 0.0, "thread": None}
KARELER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
_GLITCH = "01▓▒░<>/\\#@$%&"
FSOCIETY_FLAVOR = ["ERİŞİM SAĞLANIYOR", "PAKETLER DİNLENİYOR", "İZLER TEMİZLENİYOR",
                   "SUNUCUYA BAĞLANILIYOR", "VERİ ÇÖZÜLÜYOR", "KÖK ERİŞİMİ ARANIYOR"]


def _satir_sil():
    sys.stdout.write("\r\033[2K")
    sys.stdout.flush()


def _spin_dongu():
    i = 0
    flavor = random.choice(FSOCIETY_FLAVOR)
    while _SP["calisiyor"]:
        with _KILIT:
            if not _SP["pause"] and _SP["calisiyor"]:
                cols = shutil.get_terminal_size((60, 20)).columns
                ek = ""
                if _SP["toplam"]:
                    dolu = int(min(_SP["sayi"] / _SP["toplam"], 1) * 10)
                    ek = f" {TURUNCU}{'█' * dolu}{GRI}{'░' * (10 - dolu)}{X} {_SP['sayi']}/{_SP['toplam']}"
                sure = f" {GRI}{time.time() - _SP['t0']:.0f}s{X}"
                mesaj = _SP["mesaj"][: max(8, cols - 34)]
                if ANIM and i % 11 == 0:                       # fsociety: arada bir glitch karesi
                    kare = "".join(random.choice(_GLITCH) for _ in range(3))
                    renk, etiket = _c(46), f"{GRI}:: {flavor} ::{X}"
                else:
                    kare, renk, etiket = KARELER[i % len(KARELER)], _c(214), mesaj
                sys.stdout.write(f"\r\033[2K{renk}{kare}{X} {etiket}{ek}{sure}")
                sys.stdout.flush()
        i += 1
        time.sleep(0.08)


class Yukleniyor:
    """with Yukleniyor('mesaj', toplam) as y: ... y.adim()"""

    def __init__(self, mesaj, toplam=0):
        self.m, self.n = mesaj, toplam

    def __enter__(self):
        _SP["stack"].append((_SP["mesaj"], _SP["toplam"], _SP["sayi"]))
        _SP.update(mesaj=self.m, toplam=self.n, sayi=0)
        if ANIM and not _SP["calisiyor"]:
            _SP.update(calisiyor=True, t0=time.time())
            t = threading.Thread(target=_spin_dongu, daemon=True)
            _SP["thread"] = t
            t.start()
        return self

    def adim(self, n=1):
        _SP["sayi"] += n

    def __exit__(self, *a):
        m, t, s = _SP["stack"].pop()
        _SP.update(mesaj=m, toplam=t, sayi=s)
        if not _SP["stack"] and _SP["calisiyor"]:
            _SP["calisiyor"] = False
            if _SP["thread"]:
                _SP["thread"].join()
            with _KILIT:
                _satir_sil()
        return False


def out(m=""):
    with _KILIT:
        if _SP["calisiyor"] and not _SP["pause"]:
            _satir_sil()
        print(m + X)
    RAPOR.append(ANSI.sub("", m))


def baslik(m):
    out("")
    out(f"{MOR}╔{'═' * 58}╗")
    out(f"{MOR}║ {BOLD}{CYAN}{m:<56}{X}{MOR} ║")
    out(f"{MOR}╚{'═' * 58}╝")


def ok(m):     out(f"{YESIL}[+]{X} {m}")
def uyari(m):  out(f"{SARI}[!]{X} {SARI}{m}")
def hata(m):   out(f"{KIRMIZI}[-]{X} {KIRMIZI}{m}")
def bilgi(m):  out(f"{MAVI}[*]{X} {MAVI}{m}")
def soluk(m):  out(f"{GRI}[ ] {m}")


def kv(k, v, renk=BEYAZ):
    out(f"  {TURUNCU}{k:<16}{GRI}:{X} {renk}{v}")


def link(etiket, url):
    out(f"  {PEMBE}{etiket:<28}{X} {MAVI}{url}")


# ============================================================ HTTP
def get(url, timeout=TIMEOUT):
    """(kod, metin, başlıklar, son_url). Ağ hatasında kod=None."""
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            hdr = {k.lower(): v for k, v in r.headers.items()}
            hdr["_cookies"] = r.headers.get_all("Set-Cookie") or []
            veri = r.read(2_000_000).decode("utf-8", "replace")
            return r.status, veri, hdr, r.geturl()
    except urllib.error.HTTPError as e:
        hdr = {k.lower(): v for k, v in (e.headers or {}).items()}
        hdr["_cookies"] = []
        return e.code, "", hdr, url
    except Exception as e:
        return None, str(e), {}, url


def jget(url, timeout=TIMEOUT):
    kod, metin, _, _ = get(url, timeout)
    if kod == 200:
        try:
            return json.loads(metin)
        except Exception:
            return None
    return None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def yonlendirme_zinciri(url, maks=8):
    zincir = []
    op = urllib.request.build_opener(_NoRedirect)
    for _ in range(maks):
        try:
            with op.open(urllib.request.Request(url, headers=UA), timeout=12) as r:
                zincir.append((r.status, url))
                break
        except urllib.error.HTTPError as e:
            zincir.append((e.code, url))
            loc = e.headers.get("Location")
            if e.code in (301, 302, 303, 307, 308) and loc:
                url = urllib.parse.urljoin(url, loc)
            else:
                break
        except Exception:
            zincir.append((0, url))
            break
    return zincir


# ============================================================ YARDIMCILAR
def domain_temizle(d):
    d = d.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = d.split("/")[0].split(":")[0]
    return d[4:] if d.startswith("www.") else d


def gecerli_domain(d):
    return bool(re.match(r"^([a-z0-9-]{1,63}\.)+[a-z]{2,}$", d))


def doh(isim, tur):
    v = jget(f"https://dns.google/resolve?name={urllib.parse.quote(isim)}&type={tur}")
    if not v:
        return []
    return [a.get("data", "") for a in v.get("Answer", [])]


_SAYFA = {}


def sayfa_al(domain):
    """Ana sayfayı bir kez çekip önbellekler: ((kod,govde,hdr,url), süre, şema)."""
    if domain not in _SAYFA:
        t = time.time()
        r, sema = get(f"https://{domain}"), "https"
        if r[0] is None:
            r, sema = get(f"http://{domain}"), "http"
        _SAYFA[domain] = (r, time.time() - t, sema)
    return _SAYFA[domain]


# ============================================================ 1) KULLANICI ADI
SITELER = {
    "GitHub": "https://github.com/{}", "GitLab": "https://gitlab.com/{}",
    "Reddit": "https://www.reddit.com/user/{}", "Twitter/X": "https://x.com/{}",
    "Instagram": "https://www.instagram.com/{}/", "TikTok": "https://www.tiktok.com/@{}",
    "YouTube": "https://www.youtube.com/@{}", "Medium": "https://medium.com/@{}",
    "Dev.to": "https://dev.to/{}", "Pinterest": "https://www.pinterest.com/{}/",
    "Twitch": "https://www.twitch.tv/{}", "Telegram": "https://t.me/{}",
    "Steam": "https://steamcommunity.com/id/{}", "SoundCloud": "https://soundcloud.com/{}",
    "Behance": "https://www.behance.net/{}", "Keybase": "https://keybase.io/{}",
    "HackerNews": "https://news.ycombinator.com/user?id={}", "Replit": "https://replit.com/@{}",
    "Pastebin": "https://pastebin.com/u/{}", "About.me": "https://about.me/{}",
    "Flickr": "https://www.flickr.com/people/{}", "Vimeo": "https://vimeo.com/{}",
    "Dribbble": "https://dribbble.com/{}", "Linktree": "https://linktr.ee/{}",
    "Spotify": "https://open.spotify.com/user/{}", "Patreon": "https://www.patreon.com/{}",
    "Mastodon.social": "https://mastodon.social/@{}", "Bluesky": "https://bsky.app/profile/{}.bsky.social",
    "npm": "https://www.npmjs.com/~{}", "PyPI": "https://pypi.org/user/{}/",
    "Docker Hub": "https://hub.docker.com/u/{}", "Codeberg": "https://codeberg.org/{}",
    "Gravatar": "https://gravatar.com/{}", "Chess.com": "https://www.chess.com/member/{}",
}


def _kadi_kontrol(a):
    site, url = a
    kod, _, _, _ = get(url, timeout=12)
    return site, url, kod


def mod_kullanici(kadi):
    baslik(f"KULLANICI ADI ARAŞTIRMA: {kadi}")
    if not re.match(r"^[\w.\-]{2,40}$", kadi):
        hata("Geçersiz kullanıcı adı (2-40 karakter; harf, rakam, . _ -).")
        return
    uyari("Yalnızca herkese açık profil sayfalarının varlığına bakılır; sonuçlar kesin değildir.")
    sonuclar = []
    with Yukleniyor("Siteler taranıyor", len(SITELER)) as y:
        with cf.ThreadPoolExecutor(12) as ex:
            futs = [ex.submit(_kadi_kontrol, (s, u.format(kadi))) for s, u in SITELER.items()]
            for f in cf.as_completed(futs):
                sonuclar.append(f.result())
                y.adim()
    sira = list(SITELER)
    sonuclar.sort(key=lambda r: sira.index(r[0]))
    bulunan = []
    for site, url, kod in sonuclar:
        if kod == 200:
            ok(f"{YESIL}{site:<16}{X} MUHTEMEL VAR  {MAVI}{url}")
            bulunan.append(site)
        elif kod in (404, 410):
            soluk(f"{site:<16} yok")
        else:
            out(f"{SARI}[?]{X} {site:<16} belirsiz (HTTP {kod})")
    out("")
    ok(f"{len(bulunan)}/{len(SITELER)} sitede muhtemel profil: {', '.join(bulunan) or '-'}")


# ============================================================ 2) E-POSTA
EPOSTA_RE = re.compile(r"^[A-Za-z0-9._%+\-]{1,64}@([A-Za-z0-9\-]+\.)+[A-Za-z]{2,}$")
GECICI = {"mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com", "yopmail.com",
          "trashmail.com", "sharklasers.com", "getnada.com", "maildrop.cc", "temp-mail.org",
          "dispostable.com", "fakeinbox.com", "mintemail.com", "throwawaymail.com"}
UCRETSIZ = {"gmail.com", "outlook.com", "hotmail.com", "yahoo.com", "icloud.com", "proton.me",
            "protonmail.com", "yandex.com", "yandex.com.tr", "mail.ru", "gmx.com", "aol.com",
            "live.com", "hotmail.com.tr", "me.com"}


def mod_eposta(eposta):
    baslik(f"E-POSTA ARAŞTIRMA: {eposta}")
    eposta = eposta.strip()
    if not EPOSTA_RE.match(eposta):
        hata("E-posta biçimi geçersiz.")
        return
    ok("Biçim geçerli.")
    yerel, domain = eposta.rsplit("@", 1)
    domain = domain.lower()
    kv("Kullanıcı kısmı", yerel)
    kv("Alan adı", domain)
    if domain in GECICI:
        uyari("Bu alan adı GEÇİCİ (tek kullanımlık) e-posta servisi olarak biliniyor.")
    elif domain in UCRETSIZ:
        kv("Tür", "Ücretsiz/genel e-posta sağlayıcısı")
    else:
        kv("Tür", "Özel/kurumsal alan adı")

    out("")
    bilgi("Alan adı e-posta alabiliyor mu? (MX kontrolü)")
    mx = doh(domain, "MX")
    if mx:
        ok("MX kayıtları bulundu:")
        for m in mx[:5]:
            out(f"     {BEYAZ}{m}")
    elif doh(domain, "A"):
        uyari("MX yok ama A kaydı var (yedek olarak alan adına teslim denenebilir).")
    else:
        hata("MX/A kaydı yok: alan adı e-posta alamıyor veya mevcut değil.")

    out("")
    bilgi("Gravatar kontrolü (herkese açık avatar)")
    h = hashlib.md5(eposta.lower().encode()).hexdigest()
    kod, _, _, _ = get(f"https://www.gravatar.com/avatar/{h}?d=404&s=80", timeout=12)
    if kod == 200:
        ok("Bu e-posta için Gravatar profili/avatarı VAR.")
        link("Gravatar profili", f"https://gravatar.com/{h}")
    elif kod == 404:
        soluk("Gravatar kaydı bulunamadı.")
    else:
        uyari(f"Gravatar kontrol edilemedi (HTTP {kod}).")

    out("")
    bilgi("GitHub herkese açık arama (profilinde e-postası görünen kullanıcılar)")
    v = jget(f"https://api.github.com/search/users?q={urllib.parse.quote(eposta)}+in:email")
    if v and v.get("total_count", 0) > 0:
        for u in v["items"][:5]:
            ok(f"GitHub kullanıcısı: {u['login']}  {MAVI}{u['html_url']}")
    elif v is not None:
        soluk("GitHub'da herkese açık eşleşme yok.")
    else:
        uyari("GitHub araması yapılamadı (hız sınırı olabilir).")

    out("")
    bilgi("Arama bağlantıları (elle inceleyin):")
    for et, url in arama_baglantilari(eposta, "eposta")[:8]:
        link(et, url)
    out("")
    link("Sızıntı kontrolü (HIBP)", "https://haveibeenpwned.com/")
    uyari("Not: Bu sonuçlar adresin sahibini kesin olarak doğrulamaz.")
    uyari(f"İpucu: kullanıcı adı olarak '{yerel}' ile de arama yapabilirsiniz (Kategori 1).")


def mod_eposta_guvenlik(domain):
    baslik(f"E-POSTA GÜVENLİĞİ (SPF/DMARC/DKIM): {domain}")
    mx = doh(domain, "MX")
    if mx:
        ok("MX kayıtları:")
        for m in mx:
            out(f"     {BEYAZ}{m}")
    else:
        uyari("MX kaydı yok.")
    txt = [t.strip('"') for t in doh(domain, "TXT")]
    spf = [t for t in txt if t.lower().startswith("v=spf1")]
    if spf:
        ok(f"SPF: {spf[0]}")
        if "-all" in spf[0]:
            ok("SPF sıkı (-all).")
        elif "~all" in spf[0]:
            uyari("SPF yumuşak (~all).")
        else:
            hata("SPF zayıf/açık (?all veya +all)!")
    else:
        hata("SPF kaydı YOK.")
    dm = [t.strip('"') for t in doh(f"_dmarc.{domain}", "TXT")]
    dm = [t for t in dm if t.lower().startswith("v=dmarc1")]
    if dm:
        ok(f"DMARC: {dm[0]}")
        p = re.search(r"p=(\w+)", dm[0])
        if p:
            (ok if p.group(1).lower() in ("reject", "quarantine") else uyari)(f"DMARC politikası: {p.group(1)}")
    else:
        hata("DMARC kaydı YOK.")
    bilgi("Yaygın DKIM seçicileri deneniyor...")
    bulundu = False
    for s in ["default", "google", "selector1", "selector2", "k1", "k2", "mail", "s1", "s2", "dkim", "smtp"]:
        if doh(f"{s}._domainkey.{domain}", "TXT"):
            ok(f"DKIM bulundu: {s}._domainkey")
            bulundu = True
    if not bulundu:
        uyari("Yaygın seçicilerde DKIM bulunamadı (özel seçici olabilir).")
    for k in doh(f"_mta-sts.{domain}", "TXT"):
        ok(f"MTA-STS: {k}")


# ============================================================ 3) DOMAIN
def mod_dns(domain):
    baslik(f"DNS KAYITLARI: {domain}")
    ipler = []
    for tur in ["A", "AAAA", "MX", "NS", "TXT", "CNAME", "SOA", "CAA"]:
        kayit = doh(domain, tur)
        if kayit:
            ok(f"{BOLD}{tur}")
            for k in kayit:
                out(f"     {BEYAZ}{k}")
            if tur == "A":
                ipler = kayit
        else:
            soluk(f"{tur}: kayıt yok")
    if not ipler:
        try:
            ipler = socket.gethostbyname_ex(domain)[2]
            bilgi(f"Yedek yöntemle IP: {ipler}")
        except Exception:
            hata("IP çözümlenemedi (alan adı mevcut olmayabilir).")
    return ipler


def _alt_topla(domain):
    adlar = set()
    v = None
    for _ in range(2):
        v = jget(f"https://crt.sh/?q={urllib.parse.quote('%.' + domain)}&output=json", timeout=45)
        if v:
            break
    for k in v or []:
        for ad in k.get("name_value", "").split("\n"):
            ad = ad.strip().lower().lstrip("*.")
            if ad.endswith(domain):
                adlar.add(ad)
    kod, metin, _, _ = get(f"https://api.hackertarget.com/hostsearch/?q={domain}")
    if kod == 200 and "error" not in metin.lower()[:40]:
        for satir in metin.splitlines():
            ad = satir.split(",")[0].strip().lower()
            if ad.endswith(domain):
                adlar.add(ad)
    return sorted(adlar)


def _coz(ad):
    try:
        return ad, socket.gethostbyname(ad)
    except Exception:
        return ad, None


def mod_altalan(domain):
    baslik(f"ALT ALAN ADLARI: {domain}")
    with Yukleniyor("crt.sh / HackerTarget sorgulanıyor"):
        adlar = _alt_topla(domain)
    if not adlar:
        uyari("Alt alan adı bulunamadı veya kaynaklar yanıt vermedi.")
        return
    kontrol = adlar[:300]
    ok(f"{len(adlar)} benzersiz alt alan adı bulundu. Canlılık kontrol ediliyor...")
    sonuc = []
    with Yukleniyor("Canlılık kontrolü", len(kontrol)) as y:
        with cf.ThreadPoolExecutor(THREADS) as ex:
            futs = [ex.submit(_coz, a) for a in kontrol]
            for f in cf.as_completed(futs):
                sonuc.append(f.result())
                y.adim()
    sonuc.sort()
    canli = [(a, ip) for a, ip in sonuc if ip]
    for ad, ip in canli:
        out(f"  {YESIL}[CANLI]{X} {BEYAZ}{ad:<42}{GRI}{ip}")
    if len(adlar) > 300:
        uyari("İlk 300 kayıt kontrol edildi.")
    ok(f"Canlı: {len(canli)} / {len(kontrol)}")
    if len(kontrol) - len(canli):
        out(f"{GRI}  (Çözümlenemeyen {len(kontrol) - len(canli)} kayıt gösterilmedi)")


def mod_site_durum(domain):
    baslik(f"SİTE DURUMU: {domain}")
    (kod, govde, h, url), sure, sema = sayfa_al(domain)
    if kod is None:
        hata(f"Siteye ulaşılamadı: {govde[:90]}")
        return
    kv("Durum kodu", kod, YESIL if kod < 400 else KIRMIZI)
    kv("Yanıt süresi", f"{sure:.2f} sn", YESIL if sure < 2 else SARI)
    kv("Şema", sema.upper(), YESIL if sema == "https" else KIRMIZI)
    kv("Son URL", url)
    kv("İçerik türü", h.get("content-type", "?"))
    kv("Gövde boyutu", f"{len(govde):,} karakter (ilk 2MB)")
    m = re.search(r"<title[^>]*>(.*?)</title>", govde, re.I | re.S)
    if m:
        kv("Sayfa başlığı", m.group(1).strip()[:100])
    out("")
    bilgi("Yönlendirme zinciri (http:// başlangıcı):")
    for kd, u in yonlendirme_zinciri(f"http://{domain}"):
        out(f"     {SARI}{kd}{X} {MAVI}{u}")


def mod_domain_tam(domain):
    ipler = mod_dns(domain)
    mod_rdap(domain)
    mod_site_durum(domain)
    mod_guvenlik_hepsi(domain)
    mod_eposta_guvenlik(domain)
    for ip in sorted(set(ipler))[:3]:
        mod_ip(ip)
    mod_wayback(domain)
    mod_altalan(domain)


# ============================================================ 4) IP
def mod_ip(hedef):
    baslik(f"IP ARAŞTIRMA: {hedef}")
    hedef = hedef.strip()
    try:
        ip = ipaddress.ip_address(hedef)
        adres = str(ip)
    except ValueError:
        h = domain_temizle(hedef)
        if not gecerli_domain(h):
            hata("Geçerli bir IP adresi veya alan adı girin.")
            return
        a = doh(h, "A")
        aaaa = doh(h, "AAAA")
        bilgi(f"{h} -> A: {a or '-'}  AAAA: {aaaa or '-'}")
        if not a and not aaaa:
            hata("Çözümlenemedi.")
            return
        adres = (a or aaaa)[0]
        ip = ipaddress.ip_address(adres)
    if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
        uyari("Bu özel/yerel bir adres; genel internette sorgulanamaz.")
        return
    v = jget(f"https://ipwho.is/{adres}")
    if v and v.get("success"):
        c = v.get("connection", {})
        kv("IP", adres)
        kv("Ülke / Şehir", f"{v.get('country')} / {v.get('city')} ({v.get('region')})")
        kv("Konum (yaklaşık)", f"{v.get('latitude')}, {v.get('longitude')}")
        kv("ISS", c.get("isp"))
        kv("Kurum", c.get("org"))
        kv("ASN", c.get("asn"))
        kv("Saat dilimi", (v.get("timezone") or {}).get("id"))
        uyari("IP konumu yaklaşıktır; kişinin gerçek adresini göstermez.")
    else:
        uyari("Konum bilgisi alınamadı.")
    try:
        kv("Reverse DNS", socket.gethostbyaddr(adres)[0], YESIL)
    except Exception:
        soluk("Reverse DNS (socket) kaydı yok")
    if ip.version == 4:
        ptr = doh(".".join(reversed(adres.split("."))) + ".in-addr.arpa", "PTR")
        if ptr:
            kv("PTR (DoH)", ", ".join(ptr), YESIL)


# ============================================================ 5) GÜVENLİK
def mod_ssl(domain):
    baslik(f"SSL/TLS SERTİFİKASI: {domain}")
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=10) as s:
            with ctx.wrap_socket(s, server_hostname=domain) as ss:
                cert = ss.getpeercert()
                kv("TLS sürümü", ss.version(), YESIL if ss.version() in ("TLSv1.3", "TLSv1.2") else KIRMIZI)
                kv("Şifreleme", ss.cipher()[0])
        sub = dict(x[0] for x in cert.get("subject", []))
        iss = dict(x[0] for x in cert.get("issuer", []))
        kv("Konu (CN)", sub.get("commonName"))
        kv("Veren", f"{iss.get('organizationName')} ({iss.get('commonName')})")
        kv("Başlangıç", cert.get("notBefore"))
        kv("Bitiş", cert.get("notAfter"))
        gun = int((ssl.cert_time_to_seconds(cert["notAfter"]) - time.time()) / 86400)
        if gun < 0:
            hata(f"Sertifikanın süresi {abs(gun)} gün önce DOLMUŞ!")
        elif gun < 30:
            uyari(f"Sertifikanın bitmesine {gun} gün kaldı.")
        else:
            ok(f"Kalan süre: {gun} gün")
        san = [v for k, v in cert.get("subjectAltName", []) if k == "DNS"]
        if san:
            ok(f"SAN ({len(san)}):")
            for s_ in san[:25]:
                out(f"     {BEYAZ}{s_}")
            if len(san) > 25:
                out(f"     {GRI}... +{len(san) - 25} daha")
    except ssl.SSLCertVerificationError as e:
        hata(f"Sertifika doğrulanamadı: {e.verify_message}")
    except Exception as e:
        hata(f"SSL bağlantısı kurulamadı: {e}")


def mod_basliklar(domain):
    baslik(f"HTTP GÜVENLİK BAŞLIKLARI: {domain}")
    (kod, _, h, url), _, _ = sayfa_al(domain)
    if kod is None:
        hata("Siteye ulaşılamadı.")
        return
    kv("Sunucu", h.get("server", "gizli"))
    if "x-powered-by" in h:
        uyari(f"X-Powered-By ifşa ediyor: {h['x-powered-by']}")
    out("")
    kontrol = {"strict-transport-security": 2, "content-security-policy": 2, "x-frame-options": 1,
               "x-content-type-options": 1, "referrer-policy": 1, "permissions-policy": 1}
    puan = 0
    for k, p in kontrol.items():
        if k in h:
            puan += p
            out(f"  {YESIL}[VAR]{X} {k}")
        else:
            out(f"  {KIRMIZI}[YOK]{X} {k}")
    toplam = sum(kontrol.values())
    renk = YESIL if puan >= 6 else SARI if puan >= 3 else KIRMIZI
    out(f"  {BOLD}{renk}Güvenlik başlığı puanı: {puan}/{toplam}")
    cerezler = h.get("_cookies", [])
    if cerezler:
        out("")
        bilgi(f"Çerezler ({len(cerezler)}):")
        for c in cerezler[:6]:
            ad = c.split("=")[0]
            low = c.lower()
            bay = " ".join(f"{YESIL if e in low else KIRMIZI}{e}{X}" for e in ("secure", "httponly", "samesite"))
            out(f"     {BEYAZ}{ad:<22}{X} {bay}")


def mod_teknoloji(domain):
    baslik(f"TEKNOLOJİ TESPİTİ (pasif): {domain}")
    (kod, govde, h, url), _, _ = sayfa_al(domain)
    if kod is None:
        hata("Siteye ulaşılamadı.")
        return
    imza = {
        "WordPress": ["wp-content", "wp-includes"], "Joomla": ["/media/jui/", "joomla"],
        "Drupal": ["drupal-settings-json", "sites/default/files"], "Shopify": ["cdn.shopify.com"],
        "Wix": ["wix.com", "_wixcidx"], "Squarespace": ["squarespace.com"],
        "React": ["data-reactroot", "__next_data__"], "Next.js": ["/_next/"],
        "Vue.js": ["vue.js", "data-v-"], "Angular": ["ng-version"], "jQuery": ["jquery"],
        "Bootstrap": ["bootstrap"], "Tailwind CSS": ["tailwind"],
        "Google Analytics": ["google-analytics.com", "gtag("], "Google Tag Manager": ["googletagmanager.com"],
        "Facebook Pixel": ["fbevents.js"], "Cloudflare (CDN JS)": ["cdnjs.cloudflare.com"],
    }
    kucuk = govde.lower()
    bulunan = [t for t, im in imza.items() if any(i in kucuk for i in im)]
    g = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', govde, re.I)
    if g:
        bulunan.append(f"Generator: {g.group(1)}")
    if h.get("server"):
        bulunan.append(f"Sunucu: {h['server']}")
    if h.get("x-powered-by"):
        bulunan.append(f"Powered-By: {h['x-powered-by']}")
    cer = " ".join(h.get("_cookies", [])).lower()
    for ad, t in [("phpsessid", "PHP"), ("jsessionid", "Java"), ("asp.net_sessionid", "ASP.NET"),
                  ("laravel_session", "Laravel"), ("csrftoken", "Django")]:
        if ad in cer:
            bulunan.append(f"{t} (çerezden)")
    if any(k.startswith("cf-") for k in h):
        bulunan.append("Cloudflare CDN/WAF")
    for k, ad in [("x-amz-cf-id", "AWS CloudFront"), ("x-vercel-id", "Vercel"), ("x-sucuri-id", "Sucuri WAF"),
                  ("x-akamai-transformed", "Akamai"), ("x-served-by", "Fastly/Varnish")]:
        if k in h:
            bulunan.append(ad)
    if bulunan:
        for t in dict.fromkeys(bulunan):
            ok(t)
    else:
        soluk("Belirgin teknoloji tespit edilemedi.")


def mod_dosyalar(domain):
    baslik(f"robots.txt / SITEMAP / security.txt: {domain}")
    for yol in ["/robots.txt", "/.well-known/security.txt", "/humans.txt"]:
        kod, metin, _, _ = get(f"https://{domain}{yol}", timeout=12)
        if kod == 200 and metin.strip() and "<html" not in metin[:200].lower():
            ok(f"{yol} bulundu:")
            for s in metin.strip().splitlines()[:15]:
                out(f"     {BEYAZ}{s[:110]}")
        else:
            soluk(f"{yol}: yok")
    kod, metin, _, _ = get(f"https://{domain}/sitemap.xml", timeout=15)
    if kod == 200 and "<loc>" in metin:
        locs = re.findall(r"<loc>\s*(.*?)\s*</loc>", metin)
        ok(f"/sitemap.xml bulundu: {len(locs)} URL")
        for u in locs[:10]:
            out(f"     {MAVI}{u}")
    else:
        soluk("/sitemap.xml: yok (robots.txt içinde belirtilmiş olabilir)")


def mod_guvenlik_hepsi(domain):
    mod_ssl(domain)
    mod_basliklar(domain)
    mod_teknoloji(domain)
    mod_dosyalar(domain)


# ============================================================ 6) ARAMA BAĞLANTILARI
def arama_baglantilari(sorgu, tur="genel"):
    q = urllib.parse.quote_plus(f'"{sorgu}"')
    raw = urllib.parse.quote_plus(sorgu)
    g = "https://www.google.com/search?q="
    liste = [
        ("Google", f"{g}{q}"),
        ("Bing", f"https://www.bing.com/search?q={q}"),
        ("DuckDuckGo", f"https://duckduckgo.com/?q={q}"),
        ("Yandex", f"https://yandex.com/search/?text={q}"),
        ("Google - GitHub", f"{g}{urllib.parse.quote_plus('site:github.com ' + chr(34) + sorgu + chr(34))}"),
        ("Google - Reddit", f"{g}{urllib.parse.quote_plus('site:reddit.com ' + chr(34) + sorgu + chr(34))}"),
        ("Google - LinkedIn", f"{g}{urllib.parse.quote_plus('site:linkedin.com ' + chr(34) + sorgu + chr(34))}"),
        ("Google - X/Twitter", f"{g}{urllib.parse.quote_plus('site:x.com ' + chr(34) + sorgu + chr(34))}"),
        ("Google - Pastebin", f"{g}{urllib.parse.quote_plus('site:pastebin.com ' + chr(34) + sorgu + chr(34))}"),
        ("Google - PDF belgeler", f"{g}{urllib.parse.quote_plus(chr(34) + sorgu + chr(34) + ' filetype:pdf')}"),
        ("GitHub - kullanıcılar", f"https://github.com/search?q={raw}&type=users"),
        ("GitHub - kod", f"https://github.com/search?q={q}&type=code"),
        ("Reddit arama", f"https://www.reddit.com/search/?q={q}"),
        ("X/Twitter arama", f"https://x.com/search?q={q}"),
        ("YouTube arama", f"https://www.youtube.com/results?search_query={raw}"),
        ("Wayback (URL)", f"https://web.archive.org/web/*/{raw}"),
    ]
    if tur == "eposta" and "@" in sorgu:
        yerel = sorgu.split("@")[0]
        liste.insert(1, ("Google - yerel kısım", f"{g}{urllib.parse.quote_plus(chr(34) + yerel + chr(34))}"))
    return liste


def url_ac(url):
    for komut in (["termux-open-url"], ["xdg-open"]):
        if shutil.which(komut[0]):
            try:
                subprocess.run(komut + [url], check=False, timeout=10,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return True
            except Exception:
                pass
    try:
        import webbrowser
        return webbrowser.open(url)
    except Exception:
        return False


def mod_arama(sorgu):
    baslik(f"İNTERNET / SOSYAL PLATFORM ARAMA BAĞLANTILARI: {sorgu}")
    if len(sorgu.strip()) < 2:
        hata("Arama ifadesi çok kısa.")
        return
    tur = "eposta" if EPOSTA_RE.match(sorgu) else "genel"
    liste = arama_baglantilari(sorgu.strip(), tur)
    for i, (et, url) in enumerate(liste, 1):
        out(f"  {TURUNCU}{i:>2}.{X} {PEMBE}{et:<22}{X} {MAVI}{url}")
    if not sys.stdin.isatty():
        return
    sec = _sor("Tarayıcıda açmak için numara(lar) (örn: 1,3,5 | boş=geç):")
    for n in re.findall(r"\d+", sec):
        n = int(n)
        if 1 <= n <= len(liste):
            ok(f"Açılıyor: {liste[n - 1][0]}")
            url_ac(liste[n - 1][1])


# ============================================================ 7) EK ARAÇLAR
def mod_rdap(domain):
    baslik(f"RDAP / WHOIS KAYDI: {domain}")
    d = jget(f"https://rdap.org/domain/{domain}")
    if not d:
        uyari("RDAP sonuç vermedi (uzantı desteklemiyor olabilir; .tr gibi).")
        return
    kv("Alan adı", d.get("ldhName"))
    kv("Durum", ", ".join(d.get("status", [])))
    for o in d.get("events", []):
        kv(o.get("eventAction", "")[:16], o.get("eventDate"))
    for e in d.get("entities", []):
        vc = e.get("vcardArray", [None, []])[1]
        isim = next((x[3] for x in vc if x[0] == "fn"), None)
        if isim:
            kv("Varlık", f"{isim} ({', '.join(e.get('roles', []))})")
    ns = [n.get("ldhName") for n in d.get("nameservers", [])]
    if ns:
        kv("Nameserver", ", ".join(ns))
    if d.get("secureDNS"):
        kv("DNSSEC", d["secureDNS"])


def mod_wayback(domain):
    baslik(f"WAYBACK MACHINE: {domain}")
    v = jget(f"https://archive.org/wayback/available?url={domain}")
    snap = (v or {}).get("archived_snapshots", {}).get("closest")
    if snap:
        kv("En yakın kayıt", snap.get("timestamp"))
        link("Arşiv bağlantısı", snap.get("url"))
    else:
        uyari("Arşivde kayıt bulunamadı.")
    cdx = jget(f"https://web.archive.org/cdx/search/cdx?url={domain}&output=json"
               f"&fl=timestamp,statuscode&collapse=timestamp:4&limit=30", timeout=40)
    if cdx and len(cdx) > 1:
        ok("Arşivlenmiş yıllar: " + ", ".join(r[0][:4] for r in cdx[1:]))
        ilk = cdx[1][0]
        kv("İlk kayıt", f"{ilk[:4]}-{ilk[4:6]}-{ilk[6:8]}")
        link("İlk kayıt bağlantısı", f"https://web.archive.org/web/{ilk}/{domain}")


HASH_KALIP = [
    (r"^\$2[abxy]\$\d{2}\$[./A-Za-z0-9]{53}$", "bcrypt"),
    (r"^\$argon2(id|i|d)\$", "Argon2"),
    (r"^\$1\$", "MD5-crypt (Unix)"),
    (r"^\$5\$", "SHA-256 crypt (Unix)"),
    (r"^\$6\$", "SHA-512 crypt (Unix)"),
    (r"^\$[PH]\$", "phpass (WordPress/phpBB)"),
    (r"^\$pbkdf2", "PBKDF2"),
    (r"^pbkdf2_sha256\$", "Django PBKDF2-SHA256"),
    (r"^\{SHA\}", "LDAP SHA-1 (Base64)"),
    (r"^\*[0-9A-Fa-f]{40}$", "MySQL 4.1+ (çift SHA-1)"),
    (r"^eyJ[\w-]+\.[\w-]+\.[\w-]*$", "JWT (Base64url; hash değil, token)"),
]
HASH_UZUNLUK = {
    8: ["CRC32", "Adler-32"], 16: ["MySQL323", "yarım MD5"],
    32: ["MD5", "NTLM", "MD4", "LM"], 40: ["SHA-1", "RIPEMD-160"],
    48: ["Tiger-192"], 56: ["SHA-224", "SHA3-224"],
    64: ["SHA-256", "SHA3-256", "BLAKE2s", "RIPEMD-256"],
    96: ["SHA-384", "SHA3-384"], 128: ["SHA-512", "SHA3-512", "Whirlpool", "BLAKE2b"],
}


def hash_tani(h):
    h = h.strip()
    sonuc = [ad for kalip, ad in HASH_KALIP if re.match(kalip, h)]
    if not sonuc and re.fullmatch(r"[0-9a-fA-F]+", h):
        sonuc = HASH_UZUNLUK.get(len(h), [])
    return sonuc


def mod_hash(h):
    baslik("HASH TANIMA")
    if not h.strip():
        hata("Boş giriş.")
        return
    kv("Girdi", h[:70] + ("..." if len(h) > 70 else ""))
    kv("Uzunluk", len(h.strip()))
    s = hash_tani(h)
    if s:
        ok("Olası türler (en olası ilk sırada değildir):")
        for t in s:
            out(f"     {YESIL}• {BEYAZ}{t}")
    else:
        uyari("Bilinen bir hash biçimiyle eşleşmedi.")
    uyari("Bu araç yalnızca türü tahmin eder; hash kırmaz.")


DISCORD_EPOCH = 1420070400000


def snowflake_tarih(i):
    ms = (int(i) >> 22) + DISCORD_EPOCH
    return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc)


def mod_discord_id(sid):
    baslik("DISCORD ID -> OLUŞTURULMA TARİHİ")
    sid = sid.strip()
    if not re.fullmatch(r"\d{17,20}", sid):
        hata("Geçersiz ID (17-20 haneli sayı olmalı). Geliştirici modundan 'ID'yi kopyala'.")
        return
    kv("ID", sid)
    kv("Oluşturulma (UTC)", snowflake_tarih(sid).strftime("%Y-%m-%d %H:%M:%S"), YESIL)
    kv("Çalışan/Süreç bitleri", f"worker={(int(sid) >> 17) & 31}, process={(int(sid) >> 12) & 31}")
    v = jget(f"https://discord.com/api/guilds/{sid}/widget.json")
    if v and v.get("name"):
        ok(f"Sunucu widget'ı açık: {v['name']}  (çevrimiçi: {v.get('presence_count')})")
        if v.get("instant_invite"):
            link("Davet", v["instant_invite"])
    else:
        soluk("Sunucu widget'ı kapalı veya bu bir sunucu ID'si değil.")


def mod_discord_davet(girdi):
    baslik("DISCORD DAVET BAĞLANTISI İNCELEME")
    m = re.search(r"(?:discord\.gg/|discord(?:app)?\.com/invite/)([\w-]+)", girdi)
    kod = m.group(1) if m else girdi.strip()
    if not re.fullmatch(r"[\w-]{2,32}", kod):
        hata("Geçersiz davet kodu/bağlantısı.")
        return
    v = jget(f"https://discord.com/api/v10/invites/{urllib.parse.quote(kod)}?with_counts=true&with_expiration=true")
    if not v:
        hata("Davet geçersiz, süresi dolmuş veya sorgulanamadı.")
        return
    g = v.get("guild") or {}
    kv("Davet kodu", v.get("code"))
    kv("Sunucu adı", g.get("name"), YESIL)
    kv("Sunucu ID", g.get("id"))
    if g.get("id"):
        kv("Sunucu kuruluşu", snowflake_tarih(g["id"]).strftime("%Y-%m-%d (UTC)"))
    kv("Açıklama", (g.get("description") or "-")[:120])
    kv("Üye (yaklaşık)", v.get("approximate_member_count"))
    kv("Çevrimiçi (yaklaşık)", v.get("approximate_presence_count"))
    kv("Kanal", (v.get("channel") or {}).get("name"))
    kv("Özel URL", g.get("vanity_url_code") or "-")
    kv("Boost sayısı", g.get("premium_subscription_count"))
    kv("Bitiş", v.get("expires_at") or "süresiz")
    if g.get("features"):
        kv("Özellikler", ", ".join(g["features"][:8]))


# ============================================================ 8) EK ARAÇLAR (NORMAL dahil)
def mod_kodlama(metin):
    baslik("KODLAMA / HASH ARACI")
    kv("Girdi", metin[:80] + ("..." if len(metin) > 80 else ""))
    out("")
    ok(f"Base64  : {base64.b64encode(metin.encode()).decode()}")
    try:
        ok(f"Base64 çöz: {base64.b64decode(metin.encode(), validate=True).decode('utf-8', 'replace')}")
    except Exception:
        soluk("Base64 çöz: geçerli base64 değil")
    ok(f"URL encode: {urllib.parse.quote(metin)}")
    ok(f"URL decode: {urllib.parse.unquote(metin)}")
    ok(f"Hex     : {metin.encode().hex()}")
    out("")
    bilgi("Referans hash değerleri (kırma değil, karşılaştırma içindir):")
    for ad, fn in (("MD5", hashlib.md5), ("SHA-1", hashlib.sha1), ("SHA-256", hashlib.sha256)):
        out(f"     {ad:<8}: {fn(metin.encode()).hexdigest()}")


ULKE_KODLARI = {
    "1": "ABD/Kanada", "7": "Rusya/Kazakistan", "20": "Mısır", "27": "Güney Afrika",
    "30": "Yunanistan", "31": "Hollanda", "32": "Belçika", "33": "Fransa", "34": "İspanya",
    "36": "Macaristan", "39": "İtalya", "40": "Romanya", "41": "İsviçre", "43": "Avusturya",
    "44": "Birleşik Krallık", "45": "Danimarka", "46": "İsveç", "47": "Norveç", "48": "Polonya",
    "49": "Almanya", "51": "Peru", "52": "Meksika", "55": "Brezilya", "57": "Kolombiya",
    "60": "Malezya", "61": "Avustralya", "62": "Endonezya", "63": "Filipinler", "64": "Yeni Zelanda",
    "65": "Singapur", "66": "Tayland", "81": "Japonya", "82": "Güney Kore", "86": "Çin",
    "90": "Türkiye", "91": "Hindistan", "92": "Pakistan", "93": "Afganistan", "94": "Sri Lanka",
    "98": "İran", "211": "Güney Sudan", "212": "Fas", "213": "Cezayir", "216": "Tunus",
    "218": "Libya", "220": "Gambiya", "234": "Nijerya", "254": "Kenya", "255": "Tanzanya",
    "351": "Portekiz", "352": "Lüksemburg", "353": "İrlanda", "354": "İzlanda", "358": "Finlandiya",
    "370": "Litvanya", "371": "Letonya", "372": "Estonya", "380": "Ukrayna", "420": "Çekya",
    "421": "Slovakya", "852": "Hong Kong", "853": "Makao", "880": "Bangladeş", "886": "Tayvan",
    "960": "Maldivler", "961": "Lübnan", "962": "Ürdün", "963": "Suriye", "964": "Irak",
    "965": "Kuveyt", "966": "Suudi Arabistan", "967": "Yemen", "968": "Umman", "970": "Filistin",
    "971": "BAE", "972": "İsrail", "973": "Bahreyn", "974": "Katar", "975": "Butan",
    "992": "Tacikistan", "993": "Türkmenistan", "994": "Azerbaycan", "995": "Gürcistan",
    "996": "Kırgızistan", "998": "Özbekistan",
}


def mod_telefon(girdi):
    baslik("TELEFON NUMARASI BİÇİM KONTROLÜ")
    uyari("Bu araç yalnızca biçim/ülke kodu çözümler; numaranın sahibini bulmaz.")
    num = re.sub(r"[^\d+]", "", girdi.strip())
    kv("Girdi", girdi)
    kv("Temizlenmiş", num)
    if not num:
        hata("Numara boş.")
        return
    uluslararasi = num.startswith("+") or num.startswith("00")
    if uluslararasi:
        rakam = num.lstrip("+").lstrip("0") if num.startswith("00") else num[1:]
        bulunan = None
        for uzunluk in (3, 2, 1):
            kod = rakam[:uzunluk]
            if kod in ULKE_KODLARI:
                bulunan = kod
                break
        if bulunan:
            ok(f"Ülke kodu : +{bulunan}  ({ULKE_KODLARI[bulunan]})")
            kalan = rakam[len(bulunan):]
            kv("Yerel numara", kalan)
            kv("Yerel uzunluk", f"{len(kalan)} hane")
        else:
            uyari("Bilinen bir ülke koduyla eşleşmedi (kısa liste kullanılıyor).")
    else:
        uyari("Uluslararası biçimde değil (+ veya 00 ile başlamıyor).")
        if num.startswith("0") and len(num) == 11:
            ok(f"Türkiye yerel biçimine benziyor: +90{num[1:]}")
    rakamsayisi = len(re.sub(r"\D", "", num))
    if 7 <= rakamsayisi <= 15:
        ok(f"Uzunluk ({rakamsayisi} hane) makul bir telefon numarası aralığında (E.164: 7-15).")
    else:
        hata(f"Uzunluk ({rakamsayisi} hane) tipik telefon numarası aralığının dışında.")


PORT_TABLOSU = {
    20: "FTP (veri)", 21: "FTP (kontrol)", 22: "SSH", 23: "Telnet", 25: "SMTP",
    53: "DNS", 67: "DHCP (sunucu)", 68: "DHCP (istemci)", 69: "TFTP", 80: "HTTP",
    110: "POP3", 119: "NNTP", 123: "NTP", 135: "MSRPC", 137: "NetBIOS-NS",
    139: "NetBIOS-SSN", 143: "IMAP", 161: "SNMP", 162: "SNMP-trap", 179: "BGP",
    194: "IRC", 389: "LDAP", 443: "HTTPS", 445: "SMB", 465: "SMTPS",
    514: "Syslog", 515: "LPD", 587: "SMTP (gönderim)", 636: "LDAPS", 993: "IMAPS",
    995: "POP3S", 1080: "SOCKS proxy", 1194: "OpenVPN", 1433: "MSSQL", 1521: "Oracle DB",
    1723: "PPTP", 1883: "MQTT", 2049: "NFS", 2082: "cPanel", 2083: "cPanel (SSL)",
    2222: "SSH (alternatif)", 27017: "MongoDB", 3306: "MySQL/MariaDB", 3389: "RDP",
    3690: "SVN", 4443: "HTTPS (alternatif)", 5000: "UPnP/geliştirme", 5060: "SIP",
    5432: "PostgreSQL", 5900: "VNC", 5984: "CouchDB", 6379: "Redis", 6667: "IRC",
    8080: "HTTP proxy/alternatif", 8443: "HTTPS (alternatif)", 8883: "MQTT (SSL)",
    9000: "PHP-FPM/çeşitli", 9090: "WebSocket/çeşitli", 9200: "Elasticsearch",
    11211: "Memcached", 27015: "Oyun sunucusu (Source)",
}


def mod_port(girdi):
    baslik("İYİ BİLİNEN PORT SÖZLÜĞÜ")
    uyari("Bu bir port TARAYICI değildir; yalnızca statik bir referans sözlüğüdür.")
    girdi = girdi.strip()
    if girdi.isdigit():
        n = int(girdi)
        servis = PORT_TABLOSU.get(n)
        if servis:
            ok(f"Port {n}: {servis}")
        else:
            uyari(f"Port {n} yaygın sözlükte yok (özel/geçici port olabilir).")
    else:
        kucuk = girdi.lower()
        eslesen = [(p, s) for p, s in PORT_TABLOSU.items() if kucuk in s.lower()]
        if eslesen:
            ok(f"'{girdi}' için {len(eslesen)} eşleşme:")
            for p, s in sorted(eslesen):
                out(f"     {p:<6} {s}")
        else:
            hata("Eşleşme bulunamadı.")
    out("")
    bilgi("En sık karşılaşılan 10 port:")
    for p in (22, 25, 53, 80, 110, 143, 443, 3306, 3389, 8080):
        out(f"     {p:<6} {PORT_TABLOSU[p]}")


def mod_cve(kod):
    baslik(f"CVE AÇIKLAMA SORGUSU: {kod}")
    uyari("Bu yalnızca kamuya açık NVD veritabanından açıklama getirir; exploit kodu üretmez/çalıştırmaz.")
    kod = kod.strip().upper()
    if not re.fullmatch(r"CVE-\d{4}-\d{4,7}", kod):
        hata("Biçim hatalı. Örnek: CVE-2021-44228")
        return
    v = jget(f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={kod}", timeout=25)
    try:
        madde = v["vulnerabilities"][0]["cve"]
    except Exception:
        hata("Kayıt bulunamadı veya NVD API'sine ulaşılamadı.")
        return
    desc = next((d["value"] for d in madde.get("descriptions", []) if d["lang"] == "en"), "-")
    ok(f"ID        : {madde.get('id')}")
    kv("Yayın tarihi", madde.get("published", "-")[:10])
    kv("Güncelleme", madde.get("lastModified", "-")[:10])
    for met in madde.get("metrics", {}).values():
        if met:
            m = met[0].get("cvssData", {})
            renk = KIRMIZI if (m.get("baseScore") or 0) >= 7 else SARI if (m.get("baseScore") or 0) >= 4 else YESIL
            kv("CVSS skoru", f"{m.get('baseScore')} ({m.get('baseSeverity', met[0].get('baseSeverity','-'))})", renk)
            break
    out("")
    bilgi("Açıklama:")
    for i in range(0, len(desc), 100):
        out(f"     {desc[i:i+100]}")
    refs = [r["url"] for r in madde.get("references", [])[:5]]
    if refs:
        out("")
        bilgi("Kaynaklar:")
        for r in refs:
            out(f"     {MAVI}{r}")


# ============================================================ RAPOR
def rapor_kaydet(hedef):
    os.makedirs(RAPOR_DIZINI, exist_ok=True)
    zaman = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    yol = os.path.join(RAPOR_DIZINI, f"{re.sub(r'[^A-Za-z0-9_.-]', '_', hedef)}_{zaman}.txt")
    with open(yol, "w", encoding="utf-8") as f:
        f.write(f"OSINT-PRO Raporu | Hedef: {hedef} | {datetime.datetime.now()}\n")
        f.write("\n".join(RAPOR))
    ok(f"Rapor kaydedildi: {yol}")


# ============================================================ MENÜ
BLOKLAR = {
    "O": [" ████ ", "██  ██", "██  ██", "██  ██", " ████ "],
    "S": [" █████", "██    ", " ████ ", "    ██", "█████ "],
    "I": ["██████", "  ██  ", "  ██  ", "  ██  ", "██████"],
    "N": ["██  ██", "███ ██", "██████", "██ ███", "██  ██"],
    "T": ["██████", "  ██  ", "  ██  ", "  ██  ", "  ██  "],
}
GRAD = [220, 214, 208, 202, 166]  # turuncu tonları


def _blok_yazi(metin):
    return [" ".join(BLOKLAR[h][r] for h in metin) for r in range(5)]


def ekran_temizle():
    if sys.stdout.isatty():
        sys.stdout.write("\033[2J\033[3J\033[H")
        sys.stdout.flush()


def _yaz(metin, gecikme=0.005):
    """Daktilo efekti; ANSI renk kodlarını bozmadan yazar."""
    if not ANIM:
        print(metin)
        return
    for tok in re.split(r"(\033\[[0-9;]*m)", metin):
        if tok.startswith("\033"):
            sys.stdout.write(tok)
        else:
            for ch in tok:
                sys.stdout.write(ch)
                sys.stdout.flush()
                time.sleep(gecikme)
    sys.stdout.write("\n")
    sys.stdout.flush()


def gecis(etiket, hizli=0.012):
    """Kısa yükleme çubuğu geçişi; arada fsociety glitch karesiyle."""
    if not ANIM:
        return
    for i in range(21):
        if i in (6, 13, 18):                                    # birkaç karede glitch yanıp sönmesi
            dolu = "".join(random.choice(_GLITCH) for _ in range(i))
            sys.stdout.write(f"\r\033[2K{_c(46)}[{dolu}{GRI}{'░' * (20 - i)}{_c(46)}]{X} {_c(46)}{etiket[:20]}{X}")
        else:
            sys.stdout.write(f"\r\033[2K{_c(214)}[{'█' * i}{GRI}{'░' * (20 - i)}{_c(214)}]{X} {BEYAZ}{etiket[:20]}{X}")
        sys.stdout.flush()
        time.sleep(hizli)
    _satir_sil()


def matrix_yanip(sure=0.9, hiz=0.035):
    """Açılışta kısa bir fsociety kod-yağmuru yanıp sönmesi (bekleme ekranı süsü)."""
    if not ANIM:
        return
    c = shutil.get_terminal_size((80, 24)).columns
    gen = min(c, 70)
    yesil = _c(46)
    kareler = max(1, int(sure / hiz))
    for _ in range(kareler):
        sys.stdout.write("\r" + yesil + "".join(random.choice(_GLITCH) for _ in range(gen)) + X)
        sys.stdout.flush()
        time.sleep(hiz)
    sys.stdout.write("\r" + " " * gen + "\r")
    sys.stdout.flush()


# ---- Sağ panel: dönen küre + "THE WORLD IS YOURS" (geniş terminallerde)
RESIM_SATIR, RESIM_SUTUN, RESIM_GEN = 2, 58, 28   # görsel: OSINT yazısının hemen yanı (14 satır)
PANEL_SATIR, PANEL_SUTUN = 2, 90       # küre: görselin sağında
KURE_RX, KURE_RY = 10, 5
PANEL_GEN = 25
MIN_SUTUN, MIN_SATIR = 118, 30        # görsel + küre için en az pencere boyutu
_GL = {"calisiyor": False, "thread": None}


def _vt_ac():
    """Windows konsolunda ANSI/VT desteğini aç + UTF-8 çıktı."""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    if os.name == "nt":
        try:
            import ctypes
            k = ctypes.windll.kernel32
            h = k.GetStdHandle(-11)
            m = ctypes.c_uint()
            if k.GetConsoleMode(h, ctypes.byref(m)):
                k.SetConsoleMode(h, m.value | 0x0004)
        except Exception:
            pass
        os.system("")


def _kure(aci):
    """Orthografik projeksiyonla kıtalı, dönen küre (renkli satırlar)."""
    sat = []
    for j in range(-KURE_RY, KURE_RY + 1):
        parca, onceki = [], "?"
        for i in range(-KURE_RX, KURE_RX + 1):
            nx, ny = i / KURE_RX, j / KURE_RY
            d = nx * nx + ny * ny
            if d > 1.0:
                ch, renk = " ", None
            else:
                z = math.sqrt(1 - d)
                lat = math.asin(ny)
                lon = math.atan2(nx, z) + aci
                v = (math.sin(2.1 * lon + 0.6) * math.cos(1.7 * lat)
                     + 0.55 * math.sin(4.3 * lon - 1.2 * lat + 1.0)
                     + 0.35 * math.cos(6.0 * lat + lon))
                if d > 0.86:
                    ch, renk = "▒", 136            # atmosfer / kenar
                elif v > 0.55:
                    ch, renk = "█", (178 if d > 0.55 else 220)   # kara (altın)
                else:
                    ch, renk = "░", (17 if d > 0.55 else 25)     # okyanus
            if renk != onceki:
                parca.append(_c(renk) if renk else X)
                onceki = renk
            parca.append(ch)
        sat.append("".join(parca) + X)
    return sat


def _panel_satirlar(aci):
    pad = " " * ((PANEL_GEN - (2 * KURE_RX + 1)) // 2)
    kure = [pad + x + pad for x in _kure(aci)]
    return kure + [
        f"{_c(220)}{BOLD}{'══ THE WORLD IS YOURS ══'.center(PANEL_GEN)}{X}",
        f"{GRI}{'bilgi güçtür'.center(PANEL_GEN)}{X}",
    ]


_YER = {"mod": "yok", "resim_gen": 28, "kure_sutun": 90}


def yerlesim_sec(n=22):
    """Pencere boyutuna göre düzen: 'buyuk', 'orta' ya da 'yok'. n = menü satırı sayısı."""
    mod, gen, ks = "yok", 28, 90
    orta_satir = 16 + (n + 1) // 2 + 4
    buyuk_satir = max(40, 16 + n + 4)
    if RENK:
        c = shutil.get_terminal_size((80, 24))
        if c.columns >= 152 and c.lines >= buyuk_satir:
            mod, gen, ks = "buyuk", 64, 126
        elif c.columns >= MIN_SUTUN and c.lines >= orta_satir:
            mod, gen, ks = "orta", 28, 90
    _YER.update(mod=mod, resim_gen=gen, kure_sutun=ks, gerekli=orta_satir)
    return mod


def _globe_ciz(aci):
    cikti = "\0337"                                   # imleci kaydet
    for i, s in enumerate(_panel_satirlar(aci)):
        cikti += f"\033[{PANEL_SATIR + i};{_YER['kure_sutun']}H{s}"
    cikti += "\0338"                                  # imleci geri yükle
    with _KILIT:
        sys.stdout.write(cikti)
        sys.stdout.flush()


def _globe_dongu():
    aci = 0.0
    while _GL["calisiyor"]:
        aci += 0.16
        _globe_ciz(aci)
        time.sleep(0.12)


def globe_basla():
    _globe_ciz(0.0)
    if ANIM:
        _GL["calisiyor"] = True
        t = threading.Thread(target=_globe_dongu, daemon=True)
        _GL["thread"] = t
        t.start()


def globe_durdur():
    if _GL["calisiyor"]:
        _GL["calisiyor"] = False
        if _GL["thread"]:
            _GL["thread"].join()


_RESIM_B64 = (
    "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"
    "6DhTTHycMTHelBgfu2DjYhMTTYlJpsSUNYnJcQkJxrgEI3hDnDHaBJwK1RjkUq04UCXgirksIcoJlCoAEuMCaKOxMLCNepJR"
    "eBoGz8ATmEQftg+ZT6URMdQVK72SRbzhJE19aGCpIiiV5/coQzNtDO6Ikl9I1/QbZXymkErjK6VSg0YOqs6g1UToNFER2qgo"
    "XXSULiY6wrjaCOjGG1fHmaITEkwJCQmJyckpKUlpqUnpaclZGSlZmSlZGQuLnPSU3PTkXLDITM4GL6UkZiQnpiQnxMfGRUWC"
    "rIHupJWIpEGCQJwHGg96ChJFRKK9UQsgeaHoBByLRORSSXw/SiCDKmb744F+PLw3hwU9Kon8vCL2Rmb4vdwoqC3zu9zQIzGK"
    "VjV3PlunF/AwJKZSpoiOUEVFaGKiwmOjdfGxhjhTREJcZFJiTGKiMSXZlJoal5YSl702KSsrJSs7JTdvbX7u2sL8jOKCzNK8"
    "zLL8rFKAvIyyvPTSgvTSvDSAonVpBblr83LWZqYnJibERkdHhIeHg9QqZCICGk3EYMgAWC8qHguYM0h4Lp0kZFJFAXSZgKEI"
    "9FNJWRJ/moRCLwsJuJ+pgTpSobbkB+khbyujoKIQaEPob9XGH0v1KTKpB4EZrgopSIvOSYnIzzIWZptKs9esz02syk+qKkyu"
    "KkqtLUqvLU3fXJaxZX1OU8W6lqrcttr8zk3FnZtKuupLu+qKu+pKeupKOmoKOqrzOmvyO2vyOmpy26rzWqtymzeuayjNKM9L"
    "y8lISEuKjjPqovUqNhXP8iVw6AQuHc/38xEyyJIAqiqYoZNzo9SC+LDgeL3YaBBuNIZsCuFXqHi3c8Nflet/27TmVm70ZCT3"
    "62QxtEkH1Ud8UxQeFSxQq2U1+fFNRQlbShOay5NaK9NaK9M7qzO312b21mX3NeT1Nebv3lK8u7lkT0vZ/m2lB1pLDreXD3Vt"
    "HOracKSr/Gh3+XBPxfHujce7Ko61lw61lQ22Fg22FBxoKd7XXDqwpahn07r6ipzKwvTirISs1NUppnAxmyAO8BGxfILYPkE8"
    "koRHVQh9Q6XM6HB+YoQoPVqWFavMMimrE9XDabpmfdCZDO2zDZH3csJvpGg/XKv9OCPkj9JQqCr0XrZmp1HVUhjbVBLXUpbU"
    "XrG2szptx6bM3vp1Aw15e5vy928r3t9acqi9bKircqi76uj2quPbq04A7Kg61Vc9OlAzvqf6wu7qid3V5/bUgsWF/o3neivH"
    "dm44tb3s1PaKke0bj3Zt2NtU3FFbuLliXUXx2sKcNdnJ0YrABcJKIU0Z7KeUMjUSTrg8IFIdEBsuSIwIzjBKc0zKggRVSZJ2"
    "Y0JIuV7ctybkozL9T9XxP20w/VIc/bJU96o89HmF7l56yMOK2M6NSe0b07qq0nbUZvQ25OzekruvueBQa8lQR+mRrrKhjrLj"
    "2zec7K062Vt9qm/T2f6ac/2bxvZsnti76eLBusuHGq4ebry6YBuuHqqfPbB59kDd5b11M3s2TQOPBqrP9lUe6ajo21LaVpu7"
    "qTyzLDepIMuolXK0Mk64jKVT8QzaoEhNUEx4UEK0ON2oyI4LyU9UFSeqS5KU5WnKTeu0hfrgknD+0QzNk/I4aEM8VBYDVepe"
    "V+iuZasOJSlPN6b1NOTu2ZK/pyl/b3PBvpbiw21Fg+0AxUe6i4d7SkZ2VJzu2zjaXzneXzXaX3V+oHpqd+30gbrpQ/XXBhuv"
    "DzbODTXeGGq6dbTx1tGm20e33gV2qHl+sOkGcGpfw8W9m071Vh1ordhRl9dUkVFZlFyca9Ip+XqNICI0KEorig4HUpfERUhS"
    "YiU5CaqiFF1ZOkB4+dqw9Wna6izt+hjJGjlvR0boh41pd8vjHpVFvSiPupqp6VotLk8M29GQuWdL7oGWokPbig+3L0R7uKf8"
    "+HYQ87ITO8pGdpSd2VF2rq/yPNDGwIJOJvbUToPIH6gDYb8+2HxjsOnWUNOdo013hpvvHGu+f7zl4UjrxyPbHpzYdu/Y1ttD"
    "TXOH6mb2bjratXGgqaS1JqemNLk836QPlUSES2LCpbE6qckgi4tUJEYqMkzKdYnqwnTdhvyomkJjQ1H8lqLYTQWR7ev0mSqJ"
    "XsTZmx52oyDyUaXpSkFUR4wkRS2ViBRd1elD27L3NOXsbck90FpwpKN4ZHvZ6d4NIOAL6N0wtrPiQn8l0PbU7mrA5NKBzZf2"
    "bZ49WHf9UN38YOPdY833hpv/dmLrxyMtD0Za/nZy2+enO74c7fzibMcnp1s+Ptly/3jD9cG68f6a/a3lPZtyGyvSNxQmGfSq"
    "KL3SqJfF6mWmSFlctDIhVpWRpCvOXJ2fHp0SpzdGh0UatFq1ks8XmWSSI7nRETxGBJdWFxa4XR/cpOdtTIoICJRT2CE6Q0Rb"
    "7brB1tyjbXkn2vKOd+SNbC8F/M/1V13YUwvCDgQDAj69t/byvrqrB+uvHWq4fqjhztHm+8NND4abHo5s+/Tk1kcntz4ebf9q"
    "rOOL0c7HY13fXuj+drLnq8muxxc6Ph9rv3eiZWZvw3DXxt6GgubK9OoywD8kyiCNMciMOmlspMwUpUgxKRNMYTxBEInGR+A4"
    "cCzLxZOFIvDgnr4oHOtiXsSZVEWxghsf4NuVr3t+a096UhKBLWcH6RlBerHakJmWuD4/o74ia9eWfNA3pnZvmNlXe2Ff7dTe"
    "+pl9m0Fhzh0G8m65fXTb3eFtH41se3im88uxrsejbV+PtT8Zb3t6of3ZVNezmZ5nM73fTvR8P9n94squF1d6v7+08+lM36Ox"
    "7utDzad2Vu9tKe+qzWusSIvUS6MNsugIaWyEND5KEh8hzYoLZXODbFzorp4cNJGPIQV7kYLxVAnRX+pKEtaEisYSQ9YEkIa7"
    "86Gx2rn+em+emiGJDpBFcJWreYoYocYo0cXJI+INcWBjzW6rK93TuvHCvsa5w03XDjfdGGq+c7z9gxOdD073PBzt+WJ8++OJ"
    "7U+nd/5weecPM13Pp7pezHT9dLX7l7neX+cGfr665+XV/l+u9f96bdcvc30/z+0BTn10sn1iT93hjg07GvJbKjKMOlmsIcQU"
    "rUiIkSaulqSZQnSaEBd3fxeUnz2c7o7lY8hBGHIgFvBnqJHevFC+oD0h7OjGmLc3t/2yuzyMEUiVRgXIYzmKKK46lqdcHag2"
    "yvSJqqgUdUyqPiHLkLJOn7KuqrJsfPfW83u3XDyw5frQ1tvDrfdOdH50pvvBme0Px3d+fm7n44ldT6Z3fjvZ+91Uz/czO15c"
    "6QPkn1/Z+/2V3S8u9T2f2fXDTP+307sfnu2+dLB5sGtzW23JhtL0/Mx4pVgIDqUqMV8j4QGEyrl0OoNFYxUnq4O4gV4kAZIq"
    "xdCkOF85hRO2EhtgolChVDm0Z93nl/oMqlA/SQRHEctSxvG1Jr42LkARIzIkyqJT1LFrDQlZ0Sk5sRm5MRmFpsy8toYNg11V"
    "J7dvmt2zeW5fw+zBxmuDW+8c7/ro7PZ7Z7ffPdl7a2THvbO7Hoz2PTzX+/mFXV9M9H0x2fflRN9XF3Y9vrDrs/GdD850zw21"
    "DfY0NNeUFxdmJaUlRMcYKEQilUig+hCoRCKdhKeTSParvO1hPhiMH92fi6PwUFSpl7+CJNT7iiOxdN71+rVQnvaPsY6M3Cw/"
    "mTEoPDFYGycIXcMPjwP6AeQVxlSVaW14fGZkUs7qBf75idmFppyixk1ltw9t/uBg1dfD9d+NNT062fTJSMsX4z0/zg68vLHv"
    "2ey+ry7vfTyz+8nl3S+u7X85f+Cnmwd+vr3/9Z2Dv989+ObugV9v7v15tvfpha5bR7cd76rqqC2tKkzLTzNxaESenw/PnyRk"
    "UQUMOhpLWeHovcKRtHwV1cnDH0Hk+DCCaXwVS2liamLlKtXrpxMQdGfgYDuFo1AZ0/kaY4A0TGSIE0eYxNoYhTFFGZsRZlxr"
    "SMyKTgbkCxIyC9MLytcWrd9UXf50ZMvvY5uhS1uh+c43Vzp/udT182z/yxt7oLv7oEdHoGcj0JPj0DdHoa+OQl8fg56chL47"
    "BT0/A70ahZ6fhD4/Cn08+Ppm/1dnu6YH6nc3bwATYHHmGjGbLOFSJVyaXEBh0WjLluOW2/vYOlHsXHxgSLoHzs/Lm+1DF/jz"
    "5UyxFkfhRxt1nR01TKHMX6znaVb7BaqoojCe3hSsN4XEJGtjE/Vx6YroFGBTsnISMrNjElKSsvLTCsqqazbO7N706XDDswtt"
    "v8x2/Xy16+Xsrp9u7Pn51v63Hx2EfjgOQVcg6C4EfWi2cxB0zWxnzYtL0Den3j44+vzGvjsj2w/1bNlcU56ZkwHOPXgMEQAH"
    "LJ7g4eFt40izA5F39XN0pbrAya5omjua4YFlo0lsPC2AwhEzBSoKK5grCQvURAUoI/2VxpSwqFvxYU0J8UJ1pC41IzY9Ky4j"
    "Y3VS2rqiooyCvDUZORmFxZlFZVsaq0d311891PjwdOuzia6XV3a9nB/4/d5+6LOj0A8nIegWBP0AQb9C0BsI+t28/sZsvzMv"
    "HkHQPPTDuV/vHbk9unugt62sstKUnqOJSXSAER1dfBzhRHsYZbmDj40z1caJYutEsnMmOsN8XJBUV08aAstA4hkeeBbaO8DH"
    "PxDwlBqMLIk2QBXJUEZFagzHIkP687LkuriQqFhVdKwxOTUSVFdWfnp+cUZh6bri4oLysqrqiuEdm28Nt3x+puPFTM/Lq7ve"
    "3N0LPRyEvjkBvZ4y8/zH6y0E/Wa2b823wKPnEPQZ9PuVJ7eODO9tr67fnJhdEGZMtoNRzaDYOPosX0myXkm0dvRevpJouwrr"
    "6Ep0hvu4IMjuaBoC44vE+qFwDByZxRDJ/IJCeKoImTFZFrkmQGP0U61mqmJ4oTEirT7MlKSNiTdm5Sbl5WfkFxaUry8oq6is"
    "Kj+yp31639Y7R7e+mO6G7va9ubMX+mgQejwMvb5o1swP/40Py0FqXkLQ376aHdzR3pRdXLY6KdXOhWrvSrZZRVrusICltp6W"
    "tjjL5Sgbe5Q9DLcKToTBveEIqjuKjsQxwP7r5c3CUDgEKs+HxiEzxYxANUscGqQD+o8TRa2RRJmUxsSotKzk/Pzc9UVF60vy"
    "iovzy9bXbCo/ubvhxrFt90e2Pb3Q+etc79sPDy7U7C/nIegrs2ze/rc/8gdvfnR3fFdpWVFsRo6dM83WhWrtQLRcgVtq5bXE"
    "Er1kGcrSCmFtg7R19LJ3ITjA8c6uFGcPmp2Ht50bzRFF9sBRsGSODzOYzpVKI00RGRmhickCbYRQHSWJNkmjQf9P1CSmGrOy"
    "CzeUVjdUNm6t2bp1U+u22kN9W66c6Ph8qvf3+0Mv7x+D/rhpJv/mXyH/Lgu/Qs8vjvduKliX5QijAeVYWKKWWnla2eJt7L2X"
    "2xJX2BMd4TQXFBOOYntgWR7eAQQawyQXxQTzKvXiC5lhAwoun8YmsKVCoCJDTGRKmlQXwxJpgrVR4tDVITHxoUmpq1Oz4nNz"
    "s9eX1TbWtrdvqd9W29hUs39n472p/s9mel98ehaCvjfr4X9wvTHXy52x1g0wZ6LFMuRSa68VDqSFyl1FtXehOyGYME+OO5aL"
    "wAk8SHycr7AxWffRxvhPNxpfbYmHWk1QfshNY8gaoYjBk1E5cn+hCqiILdYGKg0irUGqj1JHxRkSU+KyszNAmqs21NRXt3c0"
    "7N/Xdm6o7daZni9meqHXdyDoR7MY/sfXL8+v7be2RllYoZfbE6ztAIgAC1lwJoCKdvLwc8ewYViGWCjaligfNIlnU0K+TpD/"
    "lqF5EM6+Gye/syZcwhbQhaoASRjgL1AYAtURwVpDsEYn10dpjXERyZlpeXn5FUU1DZU9Pc1DB9vvzQy8/HD42e0DEPQ1BP38"
    "z8p5+y/yBw3qjoWVFwj+MiuMpTXGegXe0nxrZY+zXeWzCu7njuI4o1jJSkGRmlMW7HtQ5X9LxZgJ9h1ScmvUYiOXEcQWMkVq"
    "riyUJdHwVAaJPiosMTUiLUOfnGpKSkzJSFmTlZ1bmlddW97d2XBsX9uPD0Ze3j38w4cjEPSJWfz/Dn+Qu68srXGW1l6Wy3CA"
    "uYUlevFSD0trtLWNl70zxcmVCvNgOnhQs/WCdVJGHAXXLaM/W6e6IKWX8/1TJQI1lxcQIGIEhbDEapYslKvSB5vFE5aQvDY7"
    "7atrvd/P7+poKq6u31hfv76/p25k39av5g4+n9//5qvz0CvQ8+/8e989gk3h16XLUO9gYYV638J9iaXbUit3axvUipVYW2es"
    "E9x7FYIi9KeL/X20fqTd4fypKEGbgt25JiReDmYIth9XFCDV8hX6AFmYQBMRrIkUq3Q8RdhA/Tros37oi93Qj0N7ezfv29t+"
    "drDr/LGem+O7XoDO8+NZc8///l+P+f9xvV26DL4E0LZwWbzU+X0L2BJLuMUyuOVf4dZ2CDtHT0cYYZUbEYvFaVVCuSQgyp9U"
    "GcxM4Ps2ZuqSwmRUBocukPMVoQGyUP8gNVOkEaoixdoonlzXUrQWOlYDjW2BoNFLw/VD3TXHD3deG9/3+MahN58Nm0eal/+J"
    "r3/fwm09Fr3nuGix46L3nRYtXvneEuclS2EW1k7Wdu62K9EOLjgnVxwS4+1Lp/uzuI6ueAyKyCRSeDQGlcqmcCQMvowtVvsL"
    "5UA/FIEiQBIK+idoqrGx0R+0lnzXVgh9vQ/6eejNs1OXDmyd3Nf6aHIX9OMYBD35D319/TYAScSsQrnYwmH2aLg9ytEKtsTC"
    "eckyp2XLQQrcVzggHVywTi54e2eso5u3C5ICQ5JdPSkILA1L4ZDZwX48KVeq9uOLQRZYEjVXHhas1ot1BqnOeKAi8+b6td8d"
    "q4RuboV+PgH9dOqbmZ7Hk11vPhuEoC//U9+/ByAwQjQuCEMUoLBiPJ6KQIN0LLZwXmrlsszG7IIj0m4V2smN4ILyhiG84Uiy"
    "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"
    "1KScbEmf7sk505Z7rqt4dmfZ3w5WPD5e+fmJmu/HNn93tu7paN0vl7e+udkB3e2GHg+Y92gwY1+GXhyDHux8e7vzjxsdb662"
    "vJ5uenmq9osD66/tKDnZkLG/Mtmg4UaGCwhe2OXWLivtEY6g2zi6eTgjMXA0EYGiY7FcMiWQSpEz6Sq2XyiPESFkrQ4MMIm4"
    "iTJBhjo4WxOcHyYp1Ss2rA6pNWqbYrXbEkM714TtS9efL4sbLTCOFkRfKjXNV6Xeq0v9rCX7SXfB812FP/WVvNpT8uZwJXS6"
    "HhprhKa2QrPt0LVOaL4bugWwA7q7C/riMPT5IejOzreznW8utbydaHl7dsuro7XPBtZ/0JRzomRtc0pMvkHt6gADcFvl6uEC"
    "x6OwBDTaG4VkEvBMrFcQmSCjE0KY3hoWKSyAEsHz1bMpUWxydADVxPeNFzISAhnJACLWWklAdoigQBWUr+IVhwev14k3rRZ1"
    "p2ta16i3xioH0nT7MyMOZ0UeKzCdLo07tyHhfGXKRE3qxYa02dbcuc6CuZ6C+Z6i+b7S+f6Sm33Ft/uKgb05UHx7oHh+Z8m1"
    "7SVXugsn29Zd2JY9Vr92sDShPS2yZLXKKBPI2f7WFnZWFjZWFn9dZmGzzOKvf1my3GrJcrtldi62K93sV3k6OmJcVuFdXIiu"
    "MLIHnOoBp6MQfmgEC4vi4NA8Akro4xlMxkgoOAndO4RFNfD9DIH+sTJWqoabqRXkhAUXGSQbY+Sb1ygbE9RtaYadGVF7CqIP"
    "lpiOlMSN1KScqU8fb0yfbEmb2ZZ5qS3nYnvOxa7s6dbsSx25cz2Fcz2513oKrvTkXdqWfbEpc7Jh7fna1KHiuPak8CK9JErE"
    "kfqRl7z318XvWS9539ri/eUAS5YsX7Z0uZ21HQzMzU7ORBjMBw6jI+AMtDsH6y4kIIN9MFIyLoSK1frhI1ikaDYpluuTHExP"
    "k7EzlOwCNadIE1CuE2yOlnSYQroTVH1rww5mhA/nRJ7Nj5kujrldteb+5qRPGpO/3Lb2SU/OD/1FP+0veXVk/esTlb+dqXk9"
    "tvntTMPbmS1vLmx+C3a6qaY3001vJhqh8TrodO3r4zWvDq3/pjv3Sk3yQM7q0tXKRKXQ1REOd/KAOy/AwwXh4YJEw5HeKJQ/"
    "HhdI9VH4+WgYpDA2NYLvZxT4RgmZa0QBKZKAVBkjS8nJVvJytYElYUEbDOLN0VKgmfYEVU9yaFeCqjtJuyMxbOca3eGsqGN5"
    "MSO50eP5MReKTeO50VOFprma5Nt1yfcb136yLfuTrnUfdmZ/2LPuXn/hnc60W62Z93YU3ukrnO8tmN9ZeG1b+vVtmTc7191s"
    "y76+JfNyQ9KpUtPOtLCK1dI4GVcTQLNY9BeLRRaLF1m8v8hiySILcGu5yGL5Ygt7S0sX62XuNlYoW0u03TJPhxU+MGsRxoYC"
    "syU42xJd7IgwuyCCUyDeiYV2ZmNdAvBuAqKHlO4l98PIGQSVP6bUQG5eK4gUkAxCUqTQWyfwDmXht6YFDFbIc5T+a+S+KSr/"
    "TDU7OwwojZ2pYSdIqf3rZXN7EksM/slKABArylC54lRTaKqcmqpkJsvpJik5TOgtpqM4BDcyYiUZvmLywtTCj6LPTZ2bmJyc"
    "nJqamJ6anJoG/6YnL85MXZmZvnJ56srlGbC4PTfz/cPr87Mzs1dnrl29fPXKpUcfXf/wzpXrc5dvzs/enL8G7Pz1K7duXr15"
    "69oHt2d//xbsmF8+vH/z/t35j+7O371z7e7ty3/8/BH06pOP78/euX3tzp2527fnbt2eu3vnBgB48uO3H/7+6tNPH8zfvDl7"
    "59bsrfkrT7/54OnXt29ev3L9+uW5uUtz1y5dAwSuTM9eAZQmr89O/X/+83nofwFqb5NK"
)


# ---- Görsel (sahne) : yarım-blok (▀) karakterleriyle terminalde piksel görüntü
_RESIM_N = 64
_RESIM = None


def _truecolor():
    if os.environ.get("OSINT_256"):
        return False
    if os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit"):
        return True
    if os.environ.get("TERMUX_VERSION") or "com.termux" in os.environ.get("PREFIX", ""):
        return True
    if os.name == "nt":
        try:
            return sys.getwindowsversion().build >= 15063
        except Exception:
            return False
    return False


def _x256(c):
    r, g, b = c
    if abs(r - g) < 10 and abs(g - b) < 10:
        gri = round((r - 8) / 247 * 24)
        return 16 if gri < 0 else 231 if gri > 23 else 232 + gri
    return 16 + 36 * round(r / 255 * 5) + 6 * round(g / 255 * 5) + round(b / 255 * 5)


def _resim_piksel():
    global _RESIM
    if _RESIM is None:
        ham = zlib.decompress(base64.b64decode(_RESIM_B64))
        n = _RESIM_N
        _RESIM = [[tuple(ham[(y * n + x) * 3:(y * n + x) * 3 + 3]) for x in range(n)] for y in range(n)]
    return _RESIM


def _olcekle(cols, rows2):
    src = _resim_piksel()
    n = len(src)
    cikti = []
    for y in range(rows2):
        y0 = y * n // rows2
        y1 = max(y0 + 1, (y + 1) * n // rows2)
        satir = []
        for x in range(cols):
            x0 = x * n // cols
            x1 = max(x0 + 1, (x + 1) * n // cols)
            r = g = b = c = 0
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    p = src[yy][xx]
                    r += p[0]; g += p[1]; b += p[2]; c += 1
            satir.append((r // c, g // c, b // c))
        cikti.append(satir)
    return cikti


def _resim_satirlar(cols):
    """cols sütun genişliğinde, cols/2 satırlık renkli satırlar döndürür."""
    cols = max(8, cols - cols % 2)
    px = _olcekle(cols, cols)
    tc = _truecolor()
    sat = []
    for r in range(0, cols, 2):
        parca, onceki = [], None
        for x in range(cols):
            fg, bg = px[r][x], px[r + 1][x]
            if (fg, bg) != onceki:
                if tc:
                    parca.append(f"\033[38;2;{fg[0]};{fg[1]};{fg[2]};48;2;{bg[0]};{bg[1]};{bg[2]}m")
                else:
                    parca.append(f"\033[38;5;{_x256(fg)};48;5;{_x256(bg)}m")
                onceki = (fg, bg)
            parca.append("▀")
        sat.append("".join(parca) + "\033[0m")
    return sat


def _resim_ciz(satir0, sutun0, cols=64):
    """Görseli ekranda sabit bir konuma çizer (sağ boşluk)."""
    cikti = "\0337"
    for i, s in enumerate(_resim_satirlar(cols)):
        cikti += f"\033[{satir0 + i};{sutun0}H{s}"
    cikti += "\0338"
    with _KILIT:
        sys.stdout.write(cikti)
        sys.stdout.flush()


def _tus_bekle(saniye):
    """Bir tuşa (Enter) basılana kadar ya da süre dolana kadar bekler."""
    try:
        if os.name == "nt":
            import msvcrt
            bitis = time.time() + saniye
            while time.time() < bitis:
                if msvcrt.kbhit():
                    msvcrt.getwch()
                    return
                time.sleep(0.05)
        else:
            import select
            r, _, _ = select.select([sys.stdin], [], [], saniye)
            if r:
                sys.stdin.readline()
    except Exception:
        time.sleep(saniye)


def sahne(bekle=False):
    """Tam ekran görsel: pencereye göre otomatik ölçeklenir."""
    if not RENK:
        uyari("Görsel için renkli bir terminal gerekir.")
        return
    c = shutil.get_terminal_size((80, 24))
    cols = max(16, min(_RESIM_N, c.columns - 2, (c.lines - 4) * 2))
    sat = _resim_satirlar(cols)
    ekran_temizle()
    sol = " " * max(0, (c.columns - cols) // 2)
    for s in sat:
        print(sol + s)
        if ANIM:
            sys.stdout.flush()
            time.sleep(0.025)
    yazi = "══ THE WORLD IS YOURS ══"
    print(" " * max(0, (c.columns - len(yazi)) // 2) + f"{_c(220)}{BOLD}{yazi}{X}")
    if bekle:
        _sor(f"\n{GRI}Devam etmek için Enter'a basın...{X}")


def banner(anim=False):
    ekran_temizle()
    print()
    satirlar = _blok_yazi("OSINT")
    h, w = len(satirlar), len(satirlar[0])
    if anim and ANIM:
        glit = "░▒▓#@$%&*+=?/<>"
        for k in range(-3, w + 4):          # "şifre çözme" dalgası soldan sağa
            sys.stdout.write("\033[2;1H")   # mutlak konum: Windows'ta da güvenli
            for s, c in zip(satirlar, GRAD):
                satir = ""
                for j, ch in enumerate(s):
                    if ch == " ":
                        satir += " "
                    elif j < k - 3:
                        satir += ch
                    elif j <= k + 3:
                        satir += random.choice(glit)
                    else:
                        satir += " "
                sys.stdout.write(f"  {_c(c)}{BOLD}{satir}{X}\n")
            sys.stdout.flush()
            time.sleep(0.03)
    else:
        for s, c in zip(satirlar, GRAD):
            print(f"  {_c(c)}{BOLD}{s}{X}")
    print()
    _yaz(f"  {_c(GRAD[1])}Açık Kaynak İstihbarat Çerçevesi (Yasal / Pasif){X}", 0.004)
    _yaz(f"        {_c(GRAD[2])}Hazırlandı: Termux için OSINT-PRO{X}", 0.004)
    _yaz(f"             {_c(GRAD[0])}Sürüm: 6.5 (Montana / FSOCIETY, girişsiz){X}", 0.004)
    _yaz(f"      {BEYAZ}{BOLD}Platform:{X} {CYAN}{BOLD}Termux / Linux / Windows{X}", 0.004)
    _yaz(f"  {SARI}Sadece izinli hedeflerde ve yasalara uygun kullanın.{X}", 0.003)
    print()


_GIRDI = {"eof": False}


def _sor(m):
    _SP["pause"] = True
    with _KILIT:
        if _SP["calisiyor"]:
            _satir_sil()
    try:
        return input(f"{CYAN}{m}{X} ").strip()
    except EOFError:
        _GIRDI["eof"] = True
        print()
        return ""
    except KeyboardInterrupt:
        print()
        return ""
    finally:
        _SP["pause"] = False


def girdi_al(tur):
    istem = {"domain": "Alan adı (örn: example.com):", "ip": "IP adresi veya alan adı:",
             "user": "Kullanıcı adı:", "email": "E-posta adresi:", "text": "Arama ifadesi:",
             "hash": "Hash değeri:", "discord_id": "Discord ID (sayı):",
             "discord_inv": "Davet bağlantısı veya kodu:",
             "liste": "Alan adları (virgülle) veya dosya yolu:",
             "kodlama": "Metin:", "telefon": "Telefon numarası:",
             "port": "Port numarası veya servis adı:", "cve": "CVE kodu (örn: CVE-2021-44228):"}[tur]
    v = _sor(istem)
    if not v:
        return None
    if tur == "domain":
        v = domain_temizle(v)
        if not gecerli_domain(v):
            hata("Geçersiz alan adı.")
            return None
    return v


# ============================================================ GİRİŞ / YETKİ SİSTEMİ
AYAR_DIZINI = os.environ.get("OSINT_PRO_DIZIN") or os.path.join(os.path.expanduser("~"), ".osint_pro")
AYAR_DOSYASI = os.path.join(AYAR_DIZINI, "ayar.json")
LOG_DOSYASI = os.path.join(AYAR_DIZINI, "giris.log")
ROL_SIRA = ["normal", "vip", "dost", "admin"]
ROL_SEVIYE = {"normal": 1, "vip": 2, "dost": 3, "admin": 4}
ROL_AD = {1: "NORMAL", 2: "VIP", 3: "DOST", 4: "ADMIN"}
ROL_RENK = {"normal": BEYAZ, "vip": _c(220), "dost": _c(213), "admin": KIRMIZI}
ROL_ACIKLAMA = {
    "normal": "temel araçlar",
    "vip": "normal + gelişmiş araçlar + rapor kaydetme",
    "dost": "vip + tüm araçlar + rapor görüntüleme + tema",
    "admin": "tam yetki + yönetim paneli + toplu tarama",
}

# ============================================================ ONLINE HESAP SİSTEMİ
# İstemci: OSINT_AUTH_URL=https://sunucunuz.example python osint_pro_montana_fsociety.py
# Sunucu:  python osint_pro_montana_fsociety.py --auth-server
# İnternete açarken HTTPS reverse proxy (örn. Caddy/Nginx) kullanın.
import secrets
try:
    import sqlite3           # sadece --auth-server modunda gerekir; yoksa normal kullanım etkilenmez
except ImportError:
    sqlite3 = None
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

AUTH_URL = os.environ.get("OSINT_AUTH_URL", "").strip().rstrip("/")
_AUTH = {"token": None, "user": None}
_AUTH_DB = os.environ.get("OSINT_AUTH_DB", os.path.join(AYAR_DIZINI, "accounts.sqlite3"))
_AUTH_SESSIONS = {}  # sunucu süreci belleğinde tutulan bearer token'lar


def _auth_hash(password, salt=None):
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)
    return salt.hex(), digest.hex()


def _auth_verify(password, salt_hex, digest_hex):
    try:
        return hmac.compare_digest(_auth_hash(password, bytes.fromhex(salt_hex))[1], digest_hex)
    except Exception:
        return False


def _auth_db():
    if sqlite3 is None:
        raise RuntimeError("Bu Python kurulumunda sqlite3 modülü yok; --auth-server bu yüzden kullanılamaz "
                            "(normal/yerel kullanım bundan etkilenmez).")
    os.makedirs(os.path.dirname(os.path.abspath(_AUTH_DB)), exist_ok=True)
    db = sqlite3.connect(_AUTH_DB, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE COLLATE NOCASE NOT NULL,
        salt TEXT NOT NULL, password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'normal', created_at TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1)""")
    db.commit()
    return db


def _auth_public(row):
    return {"id": row["id"], "username": row["username"], "role": row["role"],
            "created_at": row["created_at"], "active": bool(row["active"])}


def _auth_create_user(username, password, role="normal"):
    username = username.strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,32}", username):
        raise ValueError("Kullanıcı adı 3-32 karakter olmalı; harf, rakam, _, . ve - kullanılabilir.")
    if len(password) < 10:
        raise ValueError("Parola en az 10 karakter olmalı.")
    if role not in ROL_SIRA:
        raise ValueError("Geçersiz rol.")
    salt, digest = _auth_hash(password)
    with _auth_db() as db:
        db.execute("INSERT INTO users(username,salt,password_hash,role,created_at,active) VALUES(?,?,?,?,?,1)",
                   (username, salt, digest, role, datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")))


def _auth_server_main(host="127.0.0.1", port=8765):
    db = _auth_db()
    count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    db.close()
    if count == 0:
        print("\nOSINT-PRO Online Auth — ilk yönetici hesabı")
        username = os.environ.get("OSINT_ADMIN_USER") or input("Admin kullanıcı adı (3-32 karakter): ").strip()
        password = os.environ.get("OSINT_ADMIN_PASSWORD") or getpass.getpass("Admin parolası (en az 10 karakter): ")
        try:
            _auth_create_user(username, password, "admin")
        except Exception as e:
            print(f"Admin oluşturulamadı: {e}")
            return 2
        print("İlk admin hesabı oluşturuldu.")
    class Handler(BaseHTTPRequestHandler):
        server_version = "OSINT-PRO-Auth/1.0"
        def log_message(self, fmt, *args):
            # Parola/token içerebilecek istekleri standart erişim günlüğüne yazma.
            return
        def _send(self, code, obj):
            data = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(code); self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data))); self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(data)
        def _body(self):
            n = int(self.headers.get("Content-Length", "0"))
            if n < 1 or n > 16384: raise ValueError("Geçersiz istek boyutu.")
            return json.loads(self.rfile.read(n).decode("utf-8"))
        def _user(self):
            h = self.headers.get("Authorization", "")
            token = h[7:] if h.startswith("Bearer ") else ""
            uid = _AUTH_SESSIONS.get(token)
            if not uid: return None
            with _auth_db() as db:
                row = db.execute("SELECT * FROM users WHERE id=? AND active=1", (uid,)).fetchone()
            return row
        def do_GET(self):
            user = self._user()
            if not user: return self._send(401, {"error":"Oturum geçersiz. Yeniden giriş yapın."})
            if self.path == "/api/profile": return self._send(200, {"user":_auth_public(user)})
            if self.path == "/api/admin/users" and user["role"] == "admin":
                with _auth_db() as db: rows = db.execute("SELECT * FROM users ORDER BY id").fetchall()
                return self._send(200, {"users":[_auth_public(r) for r in rows]})
            return self._send(404, {"error":"Bulunamadı."})
        def do_POST(self):
            try: data = self._body()
            except Exception as e: return self._send(400, {"error":str(e)})
            path = self.path
            if path == "/api/register":
                try:
                    _auth_create_user(str(data.get("username", "")), str(data.get("password", "")), "normal")
                    return self._send(201, {"message":"Kayıt tamamlandı. Şimdi giriş yapabilirsiniz."})
                except sqlite3.IntegrityError: return self._send(409, {"error":"Bu kullanıcı adı zaten alınmış."})
                except Exception as e: return self._send(400, {"error":str(e)})
            if path == "/api/login":
                username, password = str(data.get("username", "")), str(data.get("password", ""))
                with _auth_db() as db: row = db.execute("SELECT * FROM users WHERE username=? COLLATE NOCASE", (username,)).fetchone()
                if not row or not row["active"] or not _auth_verify(password, row["salt"], row["password_hash"]):
                    return self._send(401, {"error":"Kullanıcı adı veya parola hatalı; hesap kapalı olabilir."})
                token = secrets.token_urlsafe(32); _AUTH_SESSIONS[token] = row["id"]
                return self._send(200, {"token":token, "user":_auth_public(row)})
            user = self._user()
            if not user: return self._send(401, {"error":"Oturum geçersiz. Yeniden giriş yapın."})
            if path == "/api/logout":
                h=self.headers.get("Authorization", ""); _AUTH_SESSIONS.pop(h[7:] if h.startswith("Bearer ") else "", None)
                return self._send(200, {"message":"Oturum kapatıldı."})
            if path == "/api/change-password":
                old, new = str(data.get("old_password", "")), str(data.get("new_password", ""))
                if not _auth_verify(old, user["salt"], user["password_hash"]): return self._send(401, {"error":"Mevcut parola yanlış."})
                if len(new) < 10: return self._send(400, {"error":"Yeni parola en az 10 karakter olmalı."})
                salt, digest = _auth_hash(new)
                with _auth_db() as db: db.execute("UPDATE users SET salt=?,password_hash=? WHERE id=?", (salt,digest,user["id"]))
                return self._send(200, {"message":"Parola güncellendi. Güvenlik için yeniden giriş yapın."})
            if path.startswith("/api/admin/"):
                if user["role"] != "admin": return self._send(403, {"error":"Bu işlem yalnızca ADMIN içindir."})
                try:
                    uid = int(data.get("id", 0))
                    with _auth_db() as db:
                        target = db.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
                        if not target: return self._send(404, {"error":"Kullanıcı bulunamadı."})
                        if path == "/api/admin/role":
                            role = str(data.get("role", ""))
                            if role not in ROL_SIRA: return self._send(400, {"error":"Geçersiz rol."})
                            if uid == user["id"] and role != "admin": return self._send(400, {"error":"Kendi admin rolünüzü buradan düşüremezsiniz."})
                            db.execute("UPDATE users SET role=? WHERE id=?", (role,uid))
                        elif path == "/api/admin/active":
                            active = 1 if data.get("active") else 0
                            if uid == user["id"] and not active: return self._send(400, {"error":"Kendi hesabınızı kapatamazsınız."})
                            db.execute("UPDATE users SET active=? WHERE id=?", (active,uid))
                        elif path == "/api/admin/reset-password":
                            new = str(data.get("new_password", ""))
                            if len(new) < 10: return self._send(400, {"error":"Geçici parola en az 10 karakter olmalı."})
                            salt,digest = _auth_hash(new); db.execute("UPDATE users SET salt=?,password_hash=? WHERE id=?",(salt,digest,uid))
                        else: return self._send(404, {"error":"Bulunamadı."})
                    return self._send(200, {"message":"Kullanıcı güncellendi."})
                except Exception as e: return self._send(400, {"error":str(e)})
            return self._send(404, {"error":"Bulunamadı."})
    print(f"Online auth sunucusu: http://{host}:{port}")
    if host not in ("127.0.0.1", "localhost", "::1"):
        print("UYARI: Bu yerleşik sunucu TLS sağlamaz. İnternete açmadan önce HTTPS reverse proxy arkasında çalıştırın.")
    try: ThreadingHTTPServer((host, port), Handler).serve_forever()
    except OSError as e: print(f"Sunucu başlatılamadı: {e}"); return 1
    except KeyboardInterrupt: print("\nAuth sunucusu kapatıldı.")
    return 0


def _auth_request(path, payload=None, method="GET"):
    if not AUTH_URL: raise RuntimeError("Online sunucu adresi ayarlı değil (OSINT_AUTH_URL).")
    parsed = urllib.parse.urlparse(AUTH_URL)
    if parsed.scheme != "https" and parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise RuntimeError("İnternet üzerindeki hesap sunucusu HTTPS kullanmalı; düz HTTP parola/token bilgilerini korumaz.")
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Content-Type":"application/json", "User-Agent":"OSINT-PRO-Account/1.0"}
    if _AUTH["token"]: headers["Authorization"] = "Bearer " + _AUTH["token"]
    req = urllib.request.Request(AUTH_URL + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=12) as r: return json.loads(r.read(65536).decode("utf-8"))
    except urllib.error.HTTPError as e:
        try: msg = json.loads(e.read(8192).decode("utf-8")).get("error", f"HTTP {e.code}")
        except Exception: msg = f"HTTP {e.code}"
        raise RuntimeError(msg)
    except Exception as e: raise RuntimeError(f"Sunucuya bağlanılamadı: {e}")


def _online_auth_menu():
    while True:
        baslik("MONTANA // FSOCIETY — ONLINE HESAP")
        print("  [1] Giriş yap\n  [2] Kayıt ol\n  [0] Çıkış")
        s = _sor("Seçim > ")
        if s == "0" or _GIRDI["eof"]: return None
        if s == "2":
            username = _sor("Kullanıcı adı (3-32 karakter): ").strip()
            pw = sifre_oku("Parola (en az 10 karakter): ")
            if pw is None: continue
            pw2 = sifre_oku("Parola tekrar: ")
            if pw != pw2: hata("Parolalar uyuşmuyor."); continue
            try: ok(_auth_request("/api/register", {"username":username,"password":pw}, "POST").get("message", "Kayıt tamamlandı."))
            except Exception as e: hata(str(e))
            continue
        if s == "1":
            username = _sor("Kullanıcı adı: ").strip(); pw = sifre_oku("Parola: ")
            if pw is None: continue
            try:
                result = _auth_request("/api/login", {"username":username,"password":pw}, "POST")
                _AUTH.update(token=result["token"], user=result["user"])
                rol = result["user"]["role"]
                _OTURUM.update(rol=rol, seviye=ROL_SEVIYE[rol], kapi=True)
                tema_uygula("FSOCIETY" if rol == "admin" else "Montana")
                giris_log(rol, "ONLINE GİRİŞ: " + username)
                return rol
            except Exception as e: hata(str(e))
        else: hata("Geçersiz seçim.")


def _online_profile(_=None):
    try:
        user = _auth_request("/api/profile")["user"]
        baslik("KULLANICI PROFİLİ")
        kv("Kullanıcı", user["username"]); kv("Rol", user["role"].upper())
        kv("Kayıt tarihi", user["created_at"]); kv("Durum", "Aktif" if user["active"] else "Kapalı")
    except Exception as e: hata(str(e))


def _online_change_password(_=None):
    old = sifre_oku("Mevcut parola:"); new = sifre_oku("Yeni parola (en az 10 karakter):")
    if old is None or new is None: return
    confirm = sifre_oku("Yeni parola tekrar:")
    if new != confirm: hata("Parolalar uyuşmuyor."); return
    try: ok(_auth_request("/api/change-password", {"old_password":old,"new_password":new}, "POST").get("message", "Güncellendi."))
    except Exception as e: hata(str(e))


def _online_admin_users(_=None):
    try: users = _auth_request("/api/admin/users")["users"]
    except Exception as e: hata(str(e)); return
    baslik("ONLINE KULLANICI YÖNETİMİ")
    for u in users:
        print(f"  ID:{u['id']:<4} {u['username']:<24} {u['role'].upper():<7} {'AKTİF' if u['active'] else 'KAPALI'}  {u['created_at']}")
    print("\n  [1] Rol değiştir  [2] Hesabı aç/kapat  [3] Parola sıfırla  [0] Geri")
    action = _sor("İşlem > ")
    if action == "0": return
    try: uid = int(_sor("Kullanıcı ID: "))
    except ValueError: hata("Geçersiz ID."); return
    try:
        if action == "1":
            role = _sor("Yeni rol (normal/vip/dost/admin): ").lower()
            res = _auth_request("/api/admin/role", {"id":uid,"role":role}, "POST")
        elif action == "2":
            active = _sor("Aktif olsun mu? (e/H): ").lower() == "e"
            res = _auth_request("/api/admin/active", {"id":uid,"active":active}, "POST")
        elif action == "3":
            pw = sifre_oku("Yeni geçici parola (en az 10 karakter): ")
            if pw is None: return
            res = _auth_request("/api/admin/reset-password", {"id":uid,"new_password":pw}, "POST")
        else: hata("Geçersiz işlem."); return
        ok(res.get("message", "Tamamlandı."))
    except Exception as e: hata(str(e))

_OTURUM = {"kapi": False, "rol": None, "seviye": 0, "splash": False}
TEMALAR = {
    "Altın": ([220, 214, 208, 202, 166], 208),
    "Mavi": ([123, 81, 45, 39, 33], 39),
    "Yeşil": ([157, 120, 82, 46, 34], 46),
    "Kırmızı": ([217, 210, 203, 196, 124], 196),
    "Mor": ([219, 177, 135, 129, 93], 129),
    "Montana": ([196, 160, 124, 88, 52], 196),
    "FSOCIETY": ([196, 160, 124, 88, 52], 196),
}


def tema_uygula(ad):
    global GRAD, TURUNCU
    g, a = TEMALAR.get(ad, TEMALAR["Altın"])
    GRAD = list(g)
    TURUNCU = _c(a)


def _hash_sifre(sifre, tuz=None):
    tuz = tuz or os.urandom(16)
    h = hashlib.pbkdf2_hmac("sha256", sifre.encode("utf-8"), tuz, 200_000)
    return {"tuz": tuz.hex(), "hash": h.hex()}


def _sifre_dogru(sifre, kayit):
    if not kayit:
        return False
    h = hashlib.pbkdf2_hmac("sha256", sifre.encode("utf-8"), bytes.fromhex(kayit["tuz"]), 200_000)
    return hmac.compare_digest(h.hex(), kayit["hash"])


def ayar_yukle():
    try:
        with open(AYAR_DOSYASI, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def ayar_kaydet(ayar):
    os.makedirs(AYAR_DIZINI, exist_ok=True)
    with open(AYAR_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(ayar, f, indent=2)
    try:
        os.chmod(AYAR_DOSYASI, 0o600)
    except Exception:
        pass


def giris_log(rol, durum):
    try:
        os.makedirs(AYAR_DIZINI, exist_ok=True)
        with open(LOG_DOSYASI, "a", encoding="utf-8") as f:
            f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} | {rol:<7} | {durum}\n")
    except Exception:
        pass


def sifre_oku(istem):
    """Şifreyi her tuşta '*' göstererek okur. İptal/EOF -> None."""
    sys.stdout.write(f"{CYAN}{istem}{X} ")
    sys.stdout.flush()
    try:
        if sys.stdin.isatty() and os.name == "nt":
            import msvcrt
            tus = []
            while True:
                ch = msvcrt.getwch()
                if ch in ("\r", "\n"):
                    break
                if ch == "\x03":
                    raise KeyboardInterrupt
                if ch in ("\x00", "\xe0"):          # ok tuşları vb.
                    msvcrt.getwch()
                    continue
                if ch == "\b":
                    if tus:
                        tus.pop()
                        sys.stdout.write("\b \b")
                        sys.stdout.flush()
                    continue
                tus.append(ch)
                sys.stdout.write("*")
                sys.stdout.flush()
            print()
            return "".join(tus)
        if sys.stdin.isatty():
            import termios
            import tty
            fd = sys.stdin.fileno()
            eski = termios.tcgetattr(fd)
            tus = []
            try:
                tty.setcbreak(fd, termios.TCSADRAIN)   # yapıştırılan karakterler kaybolmasın
                while True:
                    ch = sys.stdin.read(1)
                    if ch == "":
                        raise EOFError
                    if ch in ("\r", "\n"):
                        break
                    if ch == "\x03":
                        raise KeyboardInterrupt
                    if ch in ("\x7f", "\b"):
                        if tus:
                            tus.pop()
                            sys.stdout.write("\b \b")
                            sys.stdout.flush()
                        continue
                    if ch < " ":
                        continue
                    tus.append(ch)
                    sys.stdout.write("*")
                    sys.stdout.flush()
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, eski)
            print()
            return "".join(tus)
        return getpass.getpass("")                  # terminal değilse (boru hattı) yedek yöntem
    except (EOFError, KeyboardInterrupt):
        print()
        return None


def yeni_sifre_iste(ad, zorunlu=True):
    """dict = yeni şifre | None = kapalı (boş bırakıldı) | False = iptal."""
    while True:
        p1 = sifre_oku(f"{ad} (en az 4 karakter{'' if zorunlu else ', boş = kapalı'}):")
        if p1 is None:
            return False
        if p1 == "" and not zorunlu:
            return None
        if len(p1) < 4:
            hata("En az 4 karakter olmalı.")
            continue
        p2 = sifre_oku("Tekrar:")
        if p2 is None:
            return False
        if p1 != p2:
            hata("Şifreler uyuşmadı, tekrar deneyin.")
            continue
        return _hash_sifre(p1)


# Varsayılan şifrelerin tuzlu PBKDF2 hash'leri (düz metin şifre kodda yoktur)
VARSAYILAN = {
    "kapi": {"tuz": "b000112ec4b87294d00076948770ba10", "hash": "f1854e6ef3ec27c6f89a239b91326d3e7f2ad4ca191fec03a39a6891074289fc"},
    "normal": {"tuz": "44e3f07d73361251ccc5d9f710f235ff", "hash": "c7a54072a5f14cc0f0464d9b85fadcf2cb7d1f9aebb770ae965f58b038b477e6"},
    "vip": {"tuz": "f7a28dcf79587e642b1b6d9336733dc7", "hash": "eed81c0cb5c90cfb1034490ed5f660fb37b1f3ddaf4414acf4adfc2df5e3e602"},
    "dost": {"tuz": "7204c4efd3f1d6f36fb879a8948ee16b", "hash": "e97f46268de8d378406154eec610e098beced28880320a51fbf6959cd2f9d733"},
    "admin": {"tuz": "d28daee1b172d04bb933ff7ad4f4551b", "hash": "93dabf66d3179bbf13e2071bf08a6c63518088120d63ede2865ab9eda17ba6f2"},
}

def varsayilan_kur():
    """Hazır (gömülü) şifrelerle ayar dosyasını oluşturur."""
    ayar = {"surum": 1, "kapi": VARSAYILAN["kapi"], "tema": "Altın",
            "roller": {r: VARSAYILAN[r] for r in ROL_SIRA}}
    ayar_kaydet(ayar)
    return ayar


def ilk_kurulum():
    ekran_temizle()
    print(f"\n  {_c(220)}{BOLD}İLK KURULUM{X}  {GRI}Şifreleri belirleyin{X}")
    print(f"  {GRI}Kayıt yeri: {AYAR_DOSYASI}{X}\n")
    uyari("Şifreler düz metin değil, tuzlu hash olarak saklanır.")
    uyari("Unutursanız ayar dosyasını silip yeniden kurulum yapabilirsiniz.\n")
    ayar = {"surum": 1, "roller": {}, "tema": "Altın"}
    uyari("Giriş (kapı) şifresi kaldırıldı; doğrudan kategori şifreleri belirlenecek.\n")
    for rol, zorunlu in (("admin", True), ("dost", False), ("vip", False), ("normal", False)):
        k = yeni_sifre_iste(f"{rol.upper()} şifresi", zorunlu)
        if k is False:
            return None
        ayar["roller"][rol] = k
    ayar_kaydet(ayar)
    ok("Kurulum tamamlandı.")
    time.sleep(1)
    return ayar


def kapi_gec(ayar):
    for deneme in range(3):
        p = sifre_oku("Giriş şifresi:")
        if p is None:
            return False
        if _sifre_dogru(p, ayar.get("kapi")):
            giris_log("kapı", "BAŞARILI")
            gecis("Doğrulanıyor", 0.015)
            ok("Kapı açıldı.")
            return True
        giris_log("kapı", "BAŞARISIZ")
        hata(f"Yanlış şifre ({deneme + 1}/3)")
        time.sleep(1.0 * (deneme + 1))
    hata("Çok fazla hatalı deneme.")
    return False


def rol_sec(ayar):
    hatalar = 0
    while hatalar < 5:
        print(f"\n{MOR}══ {BOLD}{CYAN}KATEGORİ SEÇİN{X}{MOR} ══{X}")
        for i, r in enumerate(ROL_SIRA, 1):
            acik = (r == "normal") or ayar["roller"].get(r) is not None
            aciklama = f"{GRI}{ROL_ACIKLAMA[r]}{X}" if acik else f"{GRI}(kapalı){X}"
            print(f"  {BEYAZ}[{TURUNCU}{BOLD}{i}{X}{BEYAZ}]{X} {ROL_RENK[r]}{BOLD}{r.upper():<7}{X} {aciklama}")
        print(f"  {BEYAZ}[{KIRMIZI}{BOLD}0{X}{BEYAZ}]{X} {GRI}Çıkış{X}")
        s = _sor(f"\n{KIRMIZI}[??]{X}{CYAN} Kategori >{X}")
        if s in ("0", "q", "Q") or (s == "" and _GIRDI["eof"]):
            return None
        if not (s.isdigit() and 1 <= int(s) <= len(ROL_SIRA)):
            hata("Geçersiz seçim.")
            hatalar += 1
            continue
        rol = ROL_SIRA[int(s) - 1]
        kayit = ayar["roller"].get(rol)
        # NORMAL kategori daima şifresizdir; diğer rollerin mevcut erişim ayarları korunur.
        if rol == "normal":
            giris_log(rol, "GİRİŞ BAŞARILI (ŞİFRESİZ NORMAL)")
            return rol
        if kayit is None:
            uyari(f"{rol.upper()} kategorisi kapalı.")
            continue
        p = sifre_oku(f"{rol.upper()} şifresi:")
        if p is None:
            return None
        if _sifre_dogru(p, kayit):
            giris_log(rol, "GİRİŞ BAŞARILI")
            return rol
        giris_log(rol, "GİRİŞ BAŞARISIZ")
        hata("Yanlış şifre.")
        hatalar += 1
        time.sleep(1.0 + hatalar * 0.5)
    hata("Çok fazla hatalı deneme. Çıkılıyor.")
    return None


def giris_yap(ilk=True):
    """Başarılıysa rol adını döndürür, aksi halde None."""
    if AUTH_URL:
        banner(anim=ilk)
        return _online_auth_menu()
    if os.environ.pop("OSINT_KURULUM", "") == "1":        # kendi şifrelerinizi belirlemek için
        ayar = ilk_kurulum()
        if not ayar:
            return None
    else:
        ayar = ayar_yukle()
        if not ayar or "roller" not in ayar:
            # İlk çalıştırmada herkes kendi rol şifrelerini belirler.
            ayar = ilk_kurulum()
            if not ayar:
                return None
    banner(anim=ilk)
    print(f"  {GRI}Giriş şifresi kaldırıldı; doğrudan kategori seçin.{X}\n")
    rol = rol_sec(ayar)
    if not rol:
        return None
    _OTURUM.update(rol=rol, seviye=ROL_SEVIYE[rol])
    tema_uygula(ayar.get("tema", "Altın"))
    return rol


# ------------------------------------------------------------ Dost ve üstü ekstralar
def fsociety_animasyon(_hedef=None):
    """FSOCIETY esintili, yalnızca görsel terminal animasyonu."""
    ekran_temizle()
    kirmizi = _c(196)
    yesil = _c(46)
    beyaz = _c(255)
    satirlar = [
        "███████╗███████╗ ██████╗  ██████╗██╗███████╗████████╗██╗   ██╗",
        "██╔════╝██╔════╝██╔═══██╗██╔════╝██║██╔════╝╚══██╔══╝╚██╗ ██╔╝",
        "█████╗  ███████╗██║   ██║██║     ██║█████╗     ██║    ╚████╔╝ ",
        "██╔══╝  ╚════██║██║   ██║██║     ██║██╔══╝     ██║     ╚██╔╝  ",
        "██║     ███████║╚██████╔╝╚██████╗██║██║        ██║      ██║   ",
        "╚═╝     ╚══════╝ ╚═════╝  ╚═════╝╚═╝╚═╝        ╚═╝      ╚═╝   ",
    ]
    print(f"\n{kirmizi}{BOLD}   [ FSOCIETY // MONTANA TERMINAL ]{X}")
    if ANIM:
        matrix_yanip(0.7, 0.035)
        print()
        matrix_yanip(0.35, 0.035)
        for satir in satirlar:
            _yaz(f"{kirmizi}{BOLD}  {satir}{X}", 0.0015)
    else:
        for satir in satirlar:
            print(f"{kirmizi}{BOLD}  {satir}{X}")
    print(f"\n  {beyaz}ACCESS // {kirmizi}CONTROLLED{X}  {GRI}• Montana build • OSINT-PRO{X}")
    print(f"  {GRI}Görsel tema; gerçek bir erişim veya saldırı işlemi gerçekleştirmez.{X}\n")
    if sys.stdin.isatty():
        _sor("Menüye dönmek için Enter...")


def mod_tema():
    print(f"\n{MOR}══ {BOLD}{CYAN}TEMA SEÇ{X}{MOR} ══{X}")
    adlar = list(TEMALAR)
    for i, ad in enumerate(adlar, 1):
        g, a = TEMALAR[ad]
        onizle = "".join(f"{_c(c)}██{X}" for c in g)
        print(f"  {BEYAZ}[{TURUNCU}{BOLD}{i}{X}{BEYAZ}]{X} {ad:<8} {onizle}")
    s = _sor("Seçim (boş=geri):")
    if s.isdigit() and 1 <= int(s) <= len(adlar):
        ad = adlar[int(s) - 1]
        tema_uygula(ad)
        ayar = ayar_yukle() or {}
        ayar["tema"] = ad
        try:
            ayar_kaydet(ayar)
        except Exception:
            pass
        ok(f"Tema: {ad} (menüye dönünce uygulanır)")
        time.sleep(0.8)


def raporlar_menu(silebilir=False):
    while True:
        os.makedirs(RAPOR_DIZINI, exist_ok=True)
        dosyalar = [f for f in os.listdir(RAPOR_DIZINI) if f.endswith(".txt")]
        dosyalar.sort(key=lambda f: os.path.getmtime(os.path.join(RAPOR_DIZINI, f)), reverse=True)
        print(f"\n{MOR}══ {BOLD}{CYAN}KAYITLI RAPORLAR{X}{MOR} ══{X}  {GRI}{RAPOR_DIZINI}{X}")
        if not dosyalar:
            uyari("Kayıtlı rapor yok.")
            return
        for i, f in enumerate(dosyalar[:30], 1):
            yol = os.path.join(RAPOR_DIZINI, f)
            zaman = datetime.datetime.fromtimestamp(os.path.getmtime(yol)).strftime("%Y-%m-%d %H:%M")
            print(f"  {TURUNCU}{i:>2}.{X} {BEYAZ}{f[:44]:<44}{X} {GRI}{zaman}  {os.path.getsize(yol) // 1024 + 1} KB{X}")
        ipucu = " | d<no> sil | da hepsini sil" if silebilir else ""
        s = _sor(f"Görüntülemek için numara{ipucu} | boş=geri:").lower()
        if not s:
            return
        if silebilir and s == "da":
            if _sor("Tüm raporlar silinecek. Onay için EVET yazın:") == "EVET":
                for f in dosyalar:
                    os.remove(os.path.join(RAPOR_DIZINI, f))
                ok("Tüm raporlar silindi.")
            continue
        if silebilir and re.fullmatch(r"d\d+", s):
            n = int(s[1:])
            if 1 <= n <= min(len(dosyalar), 30):
                os.remove(os.path.join(RAPOR_DIZINI, dosyalar[n - 1]))
                ok("Silindi.")
            continue
        if s.isdigit() and 1 <= int(s) <= min(len(dosyalar), 30):
            with open(os.path.join(RAPOR_DIZINI, dosyalar[int(s) - 1]), encoding="utf-8") as f:
                for satir in f.read().splitlines()[:120]:
                    print(f"  {satir}")
            _sor(f"\n{GRI}Devam için Enter...{X}")


# ------------------------------------------------------------ Admin ekstraları
def _ssl_gun(domain):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((domain, 443), timeout=8) as s:
            with ctx.wrap_socket(s, server_hostname=domain) as ss:
                cert = ss.getpeercert()
        return int((ssl.cert_time_to_seconds(cert["notAfter"]) - time.time()) / 86400)
    except Exception:
        return None


def _toplu_tara(d):
    ips = doh(d, "A")
    kod, _, _, _ = get(f"https://{d}", timeout=12)
    txt = [t.lower() for t in doh(d, "TXT")]
    spf = any("v=spf1" in t for t in txt)
    dmarc = any("v=dmarc1" in t.lower() for t in doh(f"_dmarc.{d}", "TXT"))
    return d, (ips[0] if ips else "-"), kod, _ssl_gun(d), spf, dmarc


def mod_toplu(girdi):
    baslik("TOPLU DOMAIN TARAMASI (ADMIN)")
    if os.path.isfile(girdi):
        with open(girdi, encoding="utf-8", errors="replace") as f:
            ham = f.read().replace(",", "\n").splitlines()
    else:
        ham = girdi.replace(";", ",").split(",")
    adaylar = [domain_temizle(x) for x in ham if x.strip()]
    liste = [d for d in dict.fromkeys(adaylar) if gecerli_domain(d)][:25]
    if not liste:
        hata("Geçerli alan adı bulunamadı.")
        return
    if len(adaylar) > 25:
        uyari("En fazla 25 alan adı taranır.")
    sonuc = []
    with Yukleniyor("Alan adları taranıyor", len(liste)) as y:
        with cf.ThreadPoolExecutor(6) as ex:
            for f in cf.as_completed([ex.submit(_toplu_tara, d) for d in liste]):
                sonuc.append(f.result())
                y.adim()
    sonuc.sort()
    out(f"  {TURUNCU}{'ALAN ADI':<30}{'IP':<16}{'HTTP':<6}{'SSL(gün)':<10}{'SPF':<5}DMARC")
    for d, ip, kod, gun, spf, dmarc in sonuc:
        renk_http = YESIL if kod and kod < 400 else KIRMIZI
        renk_ssl = KIRMIZI if (gun is None or gun < 15) else YESIL
        out(f"  {BEYAZ}{d:<30}{GRI}{ip:<16}{renk_http}{str(kod):<6}{renk_ssl}{str(gun):<10}"
            f"{YESIL if spf else KIRMIZI}{'var' if spf else 'YOK':<5}{YESIL if dmarc else KIRMIZI}{'var' if dmarc else 'YOK'}")
    ok(f"{len(sonuc)} alan adı tarandı.")


def _admin_dogrula():
    ayar = ayar_yukle() or {}
    p = sifre_oku("İşlem için ADMIN şifresini girin:")
    if p is not None and _sifre_dogru(p, (ayar.get("roller") or {}).get("admin")):
        return ayar
    hata("Doğrulama başarısız.")
    giris_log("admin", "YÖNETİM DOĞRULAMA BAŞARISIZ")
    return None


def _sifre_degistir():
    ayar = _admin_dogrula()
    if not ayar:
        return
    hedefler = list(ROL_SIRA)
    for i, h in enumerate(hedefler, 1):
        print(f"  {TURUNCU}[{i}]{X} {h.upper()}")
    s = _sor("Hangi şifre değişsin? (boş=geri):")
    if not (s.isdigit() and 1 <= int(s) <= len(hedefler)):
        return
    hedef = hedefler[int(s) - 1]
    zorunlu = hedef == "admin"
    yeni = yeni_sifre_iste(f"{hedef.upper()} için yeni şifre", zorunlu)
    if yeni is False:
        return
    ayar["roller"][hedef] = yeni
    ayar_kaydet(ayar)
    giris_log("admin", f"ŞİFRE DEĞİŞTİ: {hedef}")
    ok(f"{hedef.upper()} " + ("kapatıldı." if yeni is None else "şifresi güncellendi."))


def _giris_gunlugu():
    print(f"\n{MOR}══ {BOLD}{CYAN}GİRİŞ GÜNLÜĞÜ (son 25){X}{MOR} ══{X}")
    try:
        with open(LOG_DOSYASI, encoding="utf-8") as f:
            satirlar = f.read().splitlines()[-25:]
    except Exception:
        satirlar = []
    if not satirlar:
        uyari("Günlük boş.")
    for s in satirlar:
        renk = KIRMIZI if "BAŞARISIZ" in s else YESIL if "BAŞARILI" in s else SARI
        print(f"  {renk}{s}{X}")


def _yetki_tablosu():
    print(f"\n{MOR}══ {BOLD}{CYAN}YETKİ TABLOSU{X}{MOR} ══{X}")
    print(f"  {GRI}{'Özellik':<46}{'NORMAL':<8}{'VIP':<6}{'DOST':<6}ADMIN{X}")
    for et, _, _, lv in MENU:
        hucre = "".join(f"{(YESIL + '✓' if lv <= k else KIRMIZI + '✗')}{X}{' ' * (w - 1)}"
                        for k, w in ((1, 8), (2, 6), (3, 6), (4, 5)))
        print(f"  {BEYAZ}{et:<46}{X}{hucre}")


def _ayarlari_sifirla():
    if not _admin_dogrula():
        return
    if _sor("TÜM ayarlar (şifreler, tema, günlük) silinecek. Onay için EVET yazın:") == "EVET":
        for yol in (AYAR_DOSYASI, LOG_DOSYASI):
            try:
                os.remove(yol)
            except Exception:
                pass
        ok("Ayarlar silindi. Program kapanıyor; yeniden açınca kurulum başlar.")
        raise SystemExit(0)


def admin_paneli():
    while True:
        print(f"\n{MOR}══ {BOLD}{KIRMIZI}ADMIN PANELİ{X}{MOR} ══{X}")
        secenekler = ["Şifreleri değiştir / kategori kapat", "Giriş günlüğü", "Raporları yönet (görüntüle/sil)",
                      "Yetki tablosu", "Tüm ayarları sıfırla"]
        for i, e in enumerate(secenekler, 1):
            print(f"  {BEYAZ}[{TURUNCU}{BOLD}{i}{X}{BEYAZ}]{X} {BEYAZ}{e}{X}")
        print(f"  {BEYAZ}[{KIRMIZI}{BOLD}0{X}{BEYAZ}]{X} {GRI}Geri{X}")
        s = _sor("Seçim >")
        if s in ("0", "") or (_GIRDI["eof"]):
            return
        {"1": _sifre_degistir, "2": _giris_gunlugu, "3": lambda: raporlar_menu(True),
         "4": _yetki_tablosu, "5": _ayarlari_sifirla}.get(s, lambda: hata("Geçersiz seçim."))()


# (etiket, girdi türü, fonksiyon, en düşük seviye)  1=normal 2=vip 3=dost 4=admin
MENU = [
    ("Kullanıcı Adı Araştırma", "user", mod_kullanici, 1),
    ("E-posta Adresi Bilgisi", "email", mod_eposta, 1),
    ("E-posta Alan Adı Güvenliği (SPF/DMARC)", "domain", mod_eposta_guvenlik, 2),
    ("Tam Domain Raporu (hepsi)", "domain", mod_domain_tam, 3),
    ("DNS Sorgusu", "domain", mod_dns, 1),
    ("Alt Alan Adı Keşfi", "domain", mod_altalan, 3),
    ("Site Durumu / Yönlendirmeler", "domain", mod_site_durum, 2),
    ("IP Adresi Bilgisi", "ip", mod_ip, 1),
    ("SSL Sertifikası", "domain", mod_ssl, 1),
    ("HTTP Güvenlik Başlıkları", "domain", mod_basliklar, 1),
    ("Teknoloji Tespiti", "domain", mod_teknoloji, 2),
    ("robots.txt / Sitemap / security.txt", "domain", mod_dosyalar, 2),
    ("Güvenlik Kontrolleri (hepsi)", "domain", mod_guvenlik_hepsi, 3),
    ("İnternet / Sosyal Medya Arama Bağlantıları", "text", mod_arama, 2),
    ("RDAP / WHOIS Kaydı", "domain", mod_rdap, 1),
    ("Wayback Machine Geçmişi", "domain", mod_wayback, 2),
    ("Hash Tanıma", "hash", mod_hash, 1),
    ("Discord Davet İnceleme", "discord_inv", mod_discord_davet, 3),
    ("Discord ID -> Oluşturulma Tarihi", "discord_id", mod_discord_id, 3),
    ("Sahne Ekranı (görsel)", "yok", lambda _h: sahne(), 1),
    ("FSOCIETY / Montana Animasyonları", "yok", lambda _h: fsociety_animasyon(), 1),
    ("Kayıtlı Raporlar (görüntüle)", "yok", lambda _h: raporlar_menu(False), 3),
    ("Tema Seç (renk) — Montana dahil", "yok", lambda _h: mod_tema(), 1),
    ("Online Kullanıcı Profili", "yok", lambda _h: _online_profile(), 1),
    ("Online Parola Değiştir", "yok", lambda _h: _online_change_password(), 1),
    ("Online Kullanıcı Yönetimi (ADMIN)", "yok", lambda _h: _online_admin_users(), 4),
    ("Toplu Domain Taraması", "liste", mod_toplu, 4),
    ("Admin Paneli", "yok", lambda _h: admin_paneli(), 4),
    ("Kodlama / Hash Aracı (Base64, URL, MD5...)", "kodlama", mod_kodlama, 1),
    ("Telefon Numarası Biçim Kontrolü", "telefon", mod_telefon, 1),
    ("İyi Bilinen Port Sözlüğü", "port", mod_port, 1),
    ("CVE Açıklama Sorgusu (NVD)", "cve", mod_cve, 1),
]


def calistir(etiket, tur, fn):
    gecis(etiket)
    hedef = girdi_al(tur)
    if not hedef:
        return
    RAPOR.clear()
    try:
        with Yukleniyor("Sorgulanıyor"):
            fn(hedef)
    except KeyboardInterrupt:
        uyari("İşlem durduruldu.")
    except Exception as e:
        hata(f"Beklenmeyen hata: {e}")
    if RAPOR:
        if _OTURUM["seviye"] >= 2:
            if _sor("\nRapor kaydedilsin mi? (e/H):").lower() == "e":
                rapor_kaydet(hedef)
        else:
            print(f"\n{GRI}(Rapor kaydetme VIP ve üzeri kategorilere özeldir.){X}")


def _madde(i, et, kilit=0):
    kose = f"[{i}]"
    bosluk = " " * (5 - len(kose))
    if kilit:
        return f"{GRI}[{i}]{bosluk}{et} ({ROL_AD[kilit]}+){X}"
    return f"{BEYAZ}[{TURUNCU}{BOLD}{i}{X}{BEYAZ}]{X}{bosluk}{BEYAZ}{BOLD}{et}{X}"


def menu_yaz(gorunen, seviye, rol, iki_sutun=False):
    rozet = f"{ROL_RENK[rol]}{BOLD}[ {rol.upper()} ]{X}"
    print(f"  {KIRMIZI}{BOLD}[??]{X} {KIRMIZI}{BOLD}Bir seçenek seçin:{X}   {GRI}Kategori:{X} {rozet}\n")
    tum = [_madde(i, m[0], m[3] if m[3] > seviye else 0) for i, m in enumerate(gorunen, 1)]
    tum.append(f"{BEYAZ}[{KIRMIZI}{BOLD}0{X}{BEYAZ}]{X}  {GRI}Çıkış{X}")
    tum.append(f"{BEYAZ}[{MAVI}{BOLD}L{X}{BEYAZ}]{X}  {GRI}Oturumu kapat / kategori değiştir{X}")
    if iki_sutun:
        yarim = (len(tum) + 1) // 2
        sol, sag = tum[:yarim], tum[yarim:]
        for k in range(yarim):
            a = sol[k]
            b = sag[k] if k < len(sag) else ""
            print(f"  {a}{' ' * max(1, 53 - len(ANSI.sub('', a)))}{b}")
            if ANIM:
                sys.stdout.flush()
                time.sleep(0.02)
        return
    for t in tum:
        print(f"  {t}")
        if ANIM:
            sys.stdout.flush()
            time.sleep(0.012)


def osint_animasyon_header():
    """Ana OSINT menüsünde kısa Montana/FSOCIETY terminal efekti."""
    yesil = _c(46)
    kirmizi = _c(196)
    print(f"  {kirmizi}{BOLD}MONTANA // FSOCIETY{X}  {GRI}:: OSINT NODE ::{X}")
    if ANIM and sys.stdout.isatty():
        for etiket in ("INITIALIZING", "PUBLIC SOURCES READY", "OSINT CONSOLE ONLINE"):
            sys.stdout.write(f"  {yesil}[ {etiket} ]{X}\n")
            sys.stdout.flush()
            time.sleep(0.035)
    else:
        print(f"  {yesil}[ OSINT CONSOLE ONLINE ]{X}")


def menu(rol):
    """'cikis' veya 'oturum' döndürür."""
    seviye = ROL_SEVIYE[rol]
    if RENK and ANIM and not _OTURUM["splash"] and not os.environ.get("OSINT_NOSPLASH"):
        _OTURUM["splash"] = True
        try:
            matrix_yanip(0.9, 0.04)
            sahne()
            print(f"\n{GRI}Devam etmek için Enter'a basın (4 sn sonra otomatik geçer)...{X}")
            _tus_bekle(4)
        except KeyboardInterrupt:
            pass
    while True:
        gorunen = [m for m in MENU if (AUTH_URL or not m[0].startswith("Online ")) and (m[3] <= seviye or m[3] < 4)]   # admin'e özel maddeler gizli
        banner(anim=False)
        osint_animasyon_header()
        mod = yerlesim_sec(len(gorunen) + 2)
        menu_yaz(gorunen, seviye, rol, mod == "orta")
        if mod != "yok":
            _resim_ciz(RESIM_SATIR, RESIM_SUTUN, _YER["resim_gen"])   # OSINT'in yanında görsel
            globe_basla()                                              # onun sağında dönen küre
        elif RENK:
            print(f"\n  {_c(220)}{BOLD}══ THE WORLD IS YOURS ══{X}")
            print(f"  {GRI}(Dönen küre için terminali en az {MIN_SUTUN}x{_YER['gerekli']} yapıp menüye dönün){X}")
        s = _sor(f"\n{KIRMIZI}[??]{X}{CYAN} Seçiminiz >{X}")
        globe_durdur()
        if s in ("0", "00", "q", "Q") or (s == "" and _GIRDI["eof"]):
            print()
            _yaz(f"{_c(214)}Çıkılıyor. Sorumlu kullanın!{X}", 0.02)
            return "cikis"
        if s.lower() == "l":
            giris_log(rol, "OTURUM KAPATILDI")
            if AUTH_URL and _AUTH.get("token"):
                try: _auth_request("/api/logout", {}, "POST")
                except Exception: pass
                _AUTH.update(token=None, user=None)
            return "oturum"
        if s.isdigit() and 1 <= int(s) <= len(gorunen):
            et, tur, fn, lv = gorunen[int(s) - 1]
            print()
            if lv > seviye:
                uyari(f"'{et}' {ROL_AD[lv]} ve üstü kategorilere özeldir.")
                time.sleep(1.5)
                continue
            if tur == "yok":
                fn(None)
            else:
                calistir(et, tur, fn)
            _sor(f"\n{GRI}Menüye dönmek için Enter'a basın...{X}")
        elif s != "":
            hata("Geçersiz seçim.")
            time.sleep(1)


def uygulama():
    ilk = True
    while True:
        rol = giris_yap(ilk)
        ilk = False
        if not rol:
            return
        if menu(rol) != "oturum":
            return


def cli(arg, deger):
    rol = giris_yap(ilk=False)
    if not rol:
        return
    seviye = ROL_SEVIYE[rol]
    gerekli = {"-d": 3, "-u": 1, "-e": 1, "-i": 1}
    if arg not in gerekli:
        print(__doc__)
        return
    if seviye < gerekli[arg]:
        hata(f"Bu komut {ROL_AD[gerekli[arg]]} ve üstü içindir (sizin kategoriniz: {rol.upper()}).")
        return
    RAPOR.clear()
    if arg == "-d":
        d = domain_temizle(deger)
        if not gecerli_domain(d):
            hata("Geçersiz alan adı.")
            return
        mod_domain_tam(d)
        rapor_kaydet(d)
    elif arg == "-u":
        mod_kullanici(deger)
    elif arg == "-e":
        mod_eposta(deger)
    elif arg == "-i":
        mod_ip(deger)


if __name__ == "__main__":
    if "--auth-server" in sys.argv:
        host = os.environ.get("OSINT_AUTH_HOST", "127.0.0.1")
        try: port = int(os.environ.get("OSINT_AUTH_PORT", "8765"))
        except ValueError: port = 8765
        raise SystemExit(_auth_server_main(host, port))
    _vt_ac()
    try:
        if len(sys.argv) >= 3:
            cli(sys.argv[1], sys.argv[2])
        elif len(sys.argv) == 2:
            print(__doc__)
        else:
            uygulama()
    except KeyboardInterrupt:
        print()
