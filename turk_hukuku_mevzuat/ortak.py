"""mevzuat.gov.tr istemcisinin HTTP kapısı: kimlik, site başına sıra, sert durma.

  - Sunucu kendini açıkça tanıtır: User-Agent `turk-hukuku-mevzuat-mcp/<sürüm>
    (+https://turk-hukuku.com/mcp/)`. Tarayıcıyı taklit eden başlık (Referer,
    X-Requested-With) gönderilmez; arama ucu onlarsız da yanıt veriyor (Ekim 2026'da denendi).
  - Site başına sıra: aynı siteye aynı anda tek istek gider; iki istek arasında en az
    `ARALIK` (1 sn) beklenir. FastMCP araçları worker thread'lerde çalıştığı için kilit
    `threading.Lock`'tur. Yönlendirmeler de tek tek bu kapıdan geçer.
  - Sert durma: HTTP 403 ve 429, JSON yanıtta captcha işareti, JSON beklenirken
    yönlendirme, PDF yönlendirmesinin site dışına, adressiz ya da hata sayfasına gitmesi ve
    PDF ya da JSON beklenirken HTML gelmesi `ErisimDurdu` hatası verir. İstek yinelenmez;
    captcha çözülmez, atlanmaz. Sunucu o siteye `DURMA_SURESI` boyunca (429'da Retry-After
    ne diyorsa o kadar) yeni istek göndermez ve kullanıcıyı resmî siteye yönlendirir.
  - Diğer HTTP hataları (5xx, 404 vb.) ve ağ hataları kısa bir Türkçe `KaynakHatasi`
    verir: istek yinelenmez, bekleme başlatılmaz.

mevzuat.gov.tr'nin her HTML sayfası (404 sayfası dahil) iletişim formu için grecaptcha
içerir; bu yüzden HTML sayfada captcha işareti aranmaz, beklenmeyen HTML zaten sert
durmadır (5xx ya da 404 hata sayfası hariç). Var olmayan bir PDF kimliği
/Anasayfa/ErrorPage?code=404 adresine yönlendirilir: bu "bulunamadı" demektir, sert durma
değildir. Site içindeki PDF yönlendirmesi (en çok üç adım) kapıdan geçerek izlenir.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any
from urllib.parse import parse_qs, urljoin, urlsplit

import httpx

from . import __version__

# MCP SDK günlüğü INFO düzeyinde açar; httpx de her isteği adresiyle yazar. Bu satırlar
# istemci günlüklerinde kalmasın diye httpx yalnızca uyarı yazar.
logging.getLogger("httpx").setLevel(logging.WARNING)

USER_AGENT = f"turk-hukuku-mevzuat-mcp/{__version__} (+https://turk-hukuku.com/mcp/)"
ARALIK = 1.0          # aynı siteye iki istek arasında en az bu kadar saniye
DURMA_SURESI = 120    # sert durmadan sonra o siteye istek gönderilmeyen süre (sn)
RESMI_SITE = "https://www.mevzuat.gov.tr"
_AD = "mevzuat.gov.tr"
_EN_COK_YONLENDIRME = 3

# Yalnız JSON yanıtta aranır (beklenmeyen HTML zaten sert durmadır), bu yüzden yalnız
# yapısal alanlar: "robot değilim" geçen bir sonuç ya da yansıyan sorgu siteyi durdurmasın.
_CAPTCHA = re.compile(r'"isDisplayCaptcha"\s*:\s*true|reCaptchaTimeout', re.IGNORECASE)


class ErisimDurdu(LookupError):
    """Site erişimi sınırladı, reddetti ya da doğrulama (captcha) istedi.

    Sunucu isteği yinelemez; `bekleme` saniye boyunca o siteye yeni istek göndermez.
    """

    def __init__(self, mesaj: str, bekleme: float = DURMA_SURESI):
        super().__init__(mesaj)
        self.bekleme = bekleme


class KaynakHatasi(LookupError):
    """Site geçici ya da beklenmeyen bir hata verdi (5xx, 404, ağ hatası).

    Sert durma değildir: siteye bekleme başlatılmaz. Sunucu isteği yinelemez.
    """


def durum_hatasi(r: httpx.Response) -> KaynakHatasi:
    """Sert durma sayılmayan HTTP hatası (5xx, 404 vb.) için kısa Türkçe hata."""
    kod = r.status_code
    if kod >= 500:
        neden = (f"şu anda yanıt veremiyor (HTTP {kod}, sunucu hatası). Sunucu isteği "
                 f"yinelemez; biraz sonra yeniden deneyin.")
    elif kod == 404:
        neden = "istenen adresi bulamadı (HTTP 404). Sunucu isteği yinelemez."
    elif kod >= 400:
        neden = f"isteği kabul etmedi (HTTP {kod}). Sunucu isteği yinelemez."
    else:
        neden = f"beklenmeyen bir yanıt verdi (HTTP {kod}). Sunucu isteği yinelemez."
    return KaynakHatasi(f"{_AD} {neden} Resmî site: {RESMI_SITE}")


def _resmi_mi(url: str) -> bool:
    """Yönlendirme hedefi mevzuat.gov.tr içinde mi?"""
    host = (urlsplit(url).hostname or "").lower()
    return host == "mevzuat.gov.tr" or host.endswith(".mevzuat.gov.tr")


class _Kapi:
    def __init__(self) -> None:
        self.kilit = threading.Lock()
        self.son = float("-inf")       # son isteğin bittiği an (time.monotonic)
        self.durma_bitis = 0.0
        self.durma_mesaji = ""


_kapilar: dict[str, _Kapi] = {}
_kapilar_kilidi = threading.Lock()
_gonder = httpx.request               # testler bunu sahte bir taşıyıcıyla değiştirir


def _kapi(host: str) -> _Kapi:
    with _kapilar_kilidi:
        k = _kapilar.get(host)
        if k is None:
            k = _kapilar[host] = _Kapi()
        return k


def _host(url: str) -> str:
    return urlsplit(url).hostname or url


def _durdur(url: str, hata: ErisimDurdu) -> ErisimDurdu:
    kapi = _kapi(_host(url))
    # önce mesaj, sonra süre: süreyi gören iş parçacığı mesajı da görsün; süren daha uzun
    # bir bekleme (ör. 429 Retry-After) kısaltılmaz
    kapi.durma_mesaji = str(hata)
    kapi.durma_bitis = max(kapi.durma_bitis, time.monotonic() + max(0.0, float(hata.bekleme)))
    return hata


def _sert(url: str, mesaj: str, bekleme: float = DURMA_SURESI) -> ErisimDurdu:
    return _durdur(url, ErisimDurdu(f"{mesaj} Resmî site: {RESMI_SITE}", bekleme))


def istek(yontem: str, url: str, *, headers: dict | None = None, **kw: Any) -> httpx.Response:
    """Tek HTTP kapısı: kimlik, site başına sıra ve aralık, 403/429 denetimi.

    Yönlendirme izlenmez (follow_redirects=False); çağıran her adımı yine bu kapıdan geçirir.
    Ağ hataları KaynakHatasi verir (bekleme yok, istek yinelenmez).
    """
    kapi = _kapi(_host(url))
    basliklar = {**(headers or {}), "User-Agent": USER_AGENT}
    kw["follow_redirects"] = False
    with kapi.kilit:
        kalan = kapi.durma_bitis - time.monotonic()
        if kalan > 0:
            raise ErisimDurdu(
                f"{kapi.durma_mesaji} (Bu siteye {int(kalan) + 1} sn daha istek "
                f"gönderilmeyecek.)", kalan)
        bekle = kapi.son + ARALIK - time.monotonic()
        if bekle > 0:
            time.sleep(bekle)
        try:
            r = _gonder(yontem, url, headers=basliklar, **kw)
        except httpx.TimeoutException as hata:
            raise KaynakHatasi(
                f"{_AD} zamanında yanıt vermedi (zaman aşımı). Sunucu isteği yinelemez; biraz "
                f"sonra yeniden deneyin. Resmî site: {RESMI_SITE}") from hata
        except httpx.TransportError as hata:
            raise KaynakHatasi(
                f"{_AD} ile bağlantı kurulamadı (ağ hatası). Sunucu isteği yinelemez; "
                f"bağlantınızı denetleyip biraz sonra yeniden deneyin. Resmî site: "
                f"{RESMI_SITE}") from hata
        finally:
            kapi.son = time.monotonic()
    if r.status_code == 429:
        ham = (r.headers.get("retry-after") or "").strip()
        bekleme = int(ham) if ham.isdigit() else DURMA_SURESI
        raise _sert(url, f"{_AD} erişim sınırı aşıldı; {bekleme} sn sonra tekrar deneyin. "
                         f"Sunucu isteği kendisi yinelemez.", bekleme)
    if r.status_code == 403:
        raise _sert(url, f"{_AD} isteği reddetti (HTTP 403). Sunucu yeniden denemez ve "
                         f"engeli aşmaya çalışmaz; metni resmî sitede okuyun.")
    return r


def _html_mi(r: httpx.Response) -> bool:
    tur = (r.headers.get("content-type") or "").lower()
    return "html" in tur or r.content.lstrip()[:1] == b"<"


def pdf_al(url: str, **kw: Any) -> bytes | None:
    """Resmî PDF'i indirir. Kimlik sitede yoksa None; erişim durursa ErisimDurdu; diğer
    HTTP ve ağ hatalarında KaynakHatasi."""
    for _ in range(_EN_COK_YONLENDIRME + 1):
        r = istek("GET", url, **kw)
        if 300 <= r.status_code < 400:
            hedef = r.headers.get("location") or ""
            yeni = urljoin(url, hedef)
            # önce hedefin sitede olup olmadığı: site dışındaki bir "hata sayfası" da sert durmadır
            if not hedef or not _resmi_mi(yeni):
                raise _sert(url, f"{_AD} PDF yerine site dışındaki ya da belirsiz bir adrese "
                                 f"yönlendirdi (HTTP {r.status_code}); erişim engeli ya da "
                                 f"doğrulama sayfası olabilir. Sunucu yeniden denemez.")
            if "errorpage" in hedef.lower():
                kod = (parse_qs(urlsplit(yeni).query).get("code") or [""])[0]
                if kod == "404":
                    return None
                raise _sert(url, f"{_AD} PDF yerine hata sayfasına yönlendirdi (kod "
                                 f"{kod or 'yok'}). Sunucu yeniden denemez.")
            url = yeni
            continue
        if r.status_code == 404:
            return None
        tur = (r.headers.get("content-type") or "").lower()
        if r.status_code == 200 and "pdf" in tur:
            return r.content
        if not r.is_success:
            raise durum_hatasi(r)
        if _html_mi(r):
            raise _sert(url, f"{_AD} PDF yerine bir HTML sayfası döndürdü (erişim engeli, "
                             f"doğrulama ya da bakım sayfası olabilir). Sunucu yeniden denemez.")
        raise KaynakHatasi(f"{_AD} beklenmeyen yanıt verdi (HTTP {r.status_code}, "
                           f"{tur or 'tür yok'}). Resmî site: {RESMI_SITE}")
    raise _sert(url, f"{_AD} çok fazla yönlendirme yaptı. Sunucu yeniden denemez.")


def json_al(yontem: str, url: str, **kw: Any) -> Any:
    """JSON uç noktası çağrısı. Yönlendirme, HTML, captcha ve geçersiz JSON sert durmadır;
    5xx ve 404 gibi hatalar KaynakHatasi verir (bekleme yok)."""
    r = istek(yontem, url, **kw)
    if 300 <= r.status_code < 400:
        raise _sert(url, f"{_AD} JSON yerine başka bir sayfaya yönlendirdi (HTTP "
                         f"{r.status_code}); erişim engeli ya da doğrulama sayfası olabilir. "
                         f"Sunucu yeniden denemez.")
    html = _html_mi(r)
    if not html and _CAPTCHA.search(r.text):
        raise _sert(url, f"{_AD} doğrulama (captcha) istedi. Bu sunucu captcha çözmez ve "
                         f"atlamaz; aramayı resmî sitede kendiniz yapın.")
    if not r.is_success:
        raise durum_hatasi(r)
    if html:
        raise _sert(url, f"{_AD} JSON yerine bir HTML sayfası döndürdü (erişim engeli, "
                         f"doğrulama ya da bakım sayfası olabilir). Sunucu yeniden denemez.")
    try:
        return r.json()
    except ValueError:
        raise _sert(url, f"{_AD} geçerli bir JSON yanıtı döndürmedi (beklenmeyen sayfa). "
                         f"Sunucu yeniden denemez.") from None
