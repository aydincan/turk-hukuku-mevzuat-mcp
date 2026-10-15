"""Erişim kuralları: kimlik, site başına sıra, sert durma, önbellek ve kimlik çözümü.

Ağ kullanılmaz: ortak._gonder sahte bir taşıyıcıyla değiştirilir.
Çalıştırma: python -m pytest tests
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import httpx
import pytest

from turk_hukuku_mevzuat import __version__, mevzuat, ortak, registry

PDF = "https://www.mevzuat.gov.tr/MevzuatMetin/1.5.6098.pdf"
TAKLIT_BASLIKLARI = {"referer", "origin", "x-requested-with"}


class Sahte:
    def __init__(self, yanit=None, sure: float = 0.0):
        self.kayit: list[tuple] = []
        self.yanit = yanit or (lambda yontem, url, kw: (200, {"content-type": "application/pdf"},
                                                        b"%PDF-1.4 ornek"))
        self.sure = sure
        self._kilit = threading.Lock()

    def __call__(self, yontem, url, headers=None, **kw):
        bas = time.monotonic()
        if self.sure:
            time.sleep(self.sure)
        bitis = time.monotonic()
        with self._kilit:
            self.kayit.append((bas, bitis, yontem, url, dict(headers or {}), kw))
        durum, basliklar, govde = self.yanit(yontem, url, kw)
        return httpx.Response(durum, headers=basliklar, content=govde,
                              request=httpx.Request(yontem, url))


@pytest.fixture(autouse=True)
def temiz(monkeypatch):
    ortak._kapilar.clear()
    mevzuat._CACHE.clear()
    monkeypatch.setattr(mevzuat, "_pdf_to_text", lambda veri: veri.decode("latin-1"))
    yield
    ortak._kapilar.clear()
    mevzuat._CACHE.clear()


def kur(monkeypatch, yanit=None, sure=0.0) -> Sahte:
    s = Sahte(yanit, sure)
    monkeypatch.setattr(ortak, "_gonder", s)
    return s


ARAMA_YANITI = {"draw": 1, "recordsTotal": 1, "data": [
    {"mevzuatNo": "5846", "mevAdi": "FİKİR VE SANAT ESERLERİ KANUNU", "mevzuatTur": 1,
     "mevzuatTertip": 3, "mevzuatTurEnumString": "Kanun", "kabulTarih": "05.12.1951",
     "resmiGazeteTarihi": "13.12.1951"}]}


# --- Kimlik ----------------------------------------------------------------------

def test_user_agent_durust_ve_surumlu():
    assert ortak.USER_AGENT == f"turk-hukuku-mevzuat-mcp/{__version__} (+https://turk-hukuku.com/mcp/)"
    assert "Mozilla" not in ortak.USER_AGENT


def test_arama_ve_pdf_taklit_basligi_gondermez(monkeypatch):
    def yanit(yontem, url, kw):
        if url.endswith(".pdf"):
            return 200, {"content-type": "application/pdf"}, b"MADDE 1- deneme"
        return 200, {"content-type": "application/json"}, json.dumps(ARAMA_YANITI).encode()
    s = kur(monkeypatch, yanit)
    sonuc = mevzuat.ara("fikir ve sanat")
    mevzuat.tam_metin("TBK")
    assert sonuc["sonuclar"][0]["mevzuat_id"] == "1.3.5846"
    for kayit in s.kayit:
        basliklar = {k.lower(): v for k, v in kayit[4].items()}
        assert basliklar["user-agent"] == ortak.USER_AGENT
        assert not TAKLIT_BASLIKLARI & set(basliklar)
        assert kayit[5]["follow_redirects"] is False      # yönlendirme de kapıdan geçer


# --- Site başına sıra ---------------------------------------------------------------

def test_ayni_siteye_iki_istek_en_az_bir_saniye_arayla(monkeypatch):
    s = kur(monkeypatch)
    ortak.istek("GET", "https://www.mevzuat.gov.tr/a")
    ortak.istek("GET", "https://www.mevzuat.gov.tr/b")
    (_, bitis1, *_), (bas2, *_) = s.kayit
    assert bas2 - bitis1 >= ortak.ARALIK


def test_ayni_siteye_ayni_anda_tek_istek(monkeypatch):
    s = kur(monkeypatch, sure=0.2)
    tlar = [threading.Thread(target=ortak.istek, args=("GET", f"https://www.mevzuat.gov.tr/{i}"))
            for i in range(2)]
    for t in tlar:
        t.start()
    for t in tlar:
        t.join()
    (bas1, bitis1, *_), (bas2, *_) = sorted(s.kayit)
    assert bas2 - bitis1 >= ortak.ARALIK


def test_farkli_siteler_birbirini_beklemez(monkeypatch):
    s = kur(monkeypatch)
    ortak.istek("GET", "https://www.mevzuat.gov.tr/a")
    ortak.istek("GET", "https://baska.example/a")
    (_, bitis1, *_), (bas2, *_) = s.kayit
    assert bas2 - bitis1 < 0.5


# --- Sert durma ve bulunamadı ---------------------------------------------------------

def test_404_yonlendirmesi_bulunamadi_demektir_durma_degil(monkeypatch):
    s = kur(monkeypatch, lambda y, u, kw: (302, {"location": "/Anasayfa/ErrorPage?code=404"}, b""))
    with pytest.raises(LookupError) as e:
        mevzuat.tam_metin("1.5.5846")
    assert not isinstance(e.value, ortak.ErisimDurdu)
    assert "bulunamadı" in str(e.value)
    assert len(s.kayit) == 1                               # hata sayfası indirilmez
    with pytest.raises(LookupError) as e:                  # site için bekleme başlamadı
        mevzuat.tam_metin("1.5.5846")
    assert not isinstance(e.value, ortak.ErisimDurdu)
    assert len(s.kayit) == 2


def test_baska_hata_sayfasina_yonlendirme_durur(monkeypatch):
    kur(monkeypatch, lambda y, u, kw: (302, {"location": "/Anasayfa/ErrorPage?code=429"}, b""))
    with pytest.raises(ortak.ErisimDurdu):
        mevzuat.tam_metin("TBK")


def test_pdf_yerine_html_durur(monkeypatch):
    sayfa = b"<!DOCTYPE html><html><script>grecaptcha.reset();</script></html>"
    s = kur(monkeypatch, lambda y, u, kw: (200, {"content-type": "text/html; charset=utf-8"}, sayfa))
    with pytest.raises(ortak.ErisimDurdu) as e:
        mevzuat.madde("TBK", 49)
    assert "PDF yerine bir HTML sayfası" in str(e.value)
    assert "https://www.mevzuat.gov.tr" in str(e.value)
    with pytest.raises(ortak.ErisimDurdu) as e:           # bekleme sürüyor: ağa gidilmez
        mevzuat.madde("TMK", 1)
    assert "sn daha istek gönderilmeyecek" in str(e.value)
    assert len(s.kayit) == 1


@pytest.mark.parametrize("durum, parca", [(403, "HTTP 403"), (429, "erişim sınırı aşıldı; 45 sn")])
def test_403_ve_429_durur_yeniden_denemez(monkeypatch, durum, parca):
    s = kur(monkeypatch, lambda y, u, kw: (durum, {"retry-after": "45"}, b""))
    with pytest.raises(ortak.ErisimDurdu) as e:
        mevzuat.ara("borçlar")
    assert parca in str(e.value)
    assert len(s.kayit) == 1


def test_aramada_html_durur(monkeypatch):
    kur(monkeypatch, lambda y, u, kw: (200, {"content-type": "text/html"}, b"<html>Bakim</html>"))
    with pytest.raises(ortak.ErisimDurdu) as e:
        mevzuat.ara("borçlar")
    assert "JSON yerine bir HTML sayfası" in str(e.value)


def test_aramada_captcha_isareti_durur(monkeypatch):
    kur(monkeypatch, lambda y, u, kw: (200, {"content-type": "application/json"},
                                       b'{"isDisplayCaptcha": true}'))
    with pytest.raises(ortak.ErisimDurdu) as e:
        mevzuat.ara("borçlar")
    assert "captcha" in str(e.value)


def test_aramada_yansiyan_sorgu_captcha_sayilmaz(monkeypatch):
    # "robot değilim" ya da "grecaptcha" geçen bir sonuç (ya da yansıyan sorgu) JSON'dur,
    # doğrulama isteği değildir; site durdurulmamalı.
    veri = {"draw": 1, "recordsTotal": 1, "data": [
        {**ARAMA_YANITI["data"][0], "mevAdi": "<span>robot değilim</span> grecaptcha"}]}
    s = kur(monkeypatch, lambda y, u, kw: (200, {"content-type": "application/json"},
                                           json.dumps(veri, ensure_ascii=False).encode("utf-8")))
    assert mevzuat.ara("robot değilim")["sonuclar"][0]["mevzuat_id"] == "1.3.5846"
    mevzuat.ara("ikinci")                                  # bekleme başlamadı
    assert len(s.kayit) == 2


def test_pdf_yonlendirmesi_kapidan_gecerek_izlenir(monkeypatch):
    def yanit(yontem, url, kw):
        if url == PDF:
            return 301, {"location": "/MevzuatMetin/yeni.pdf"}, b""
        return 200, {"content-type": "application/pdf"}, b"MADDE 1- deneme"
    s = kur(monkeypatch, yanit)
    assert ortak.pdf_al(PDF) == b"MADDE 1- deneme"
    assert [k[3] for k in s.kayit] == [PDF, "https://www.mevzuat.gov.tr/MevzuatMetin/yeni.pdf"]
    assert s.kayit[1][0] - s.kayit[0][1] >= ortak.ARALIK


def test_pdf_yonlendirmesi_ana_alan_adina_da_izlenir(monkeypatch):
    hedef = "https://mevzuat.gov.tr/MevzuatMetin/1.5.6098.pdf"

    def yanit(yontem, url, kw):
        if url == PDF:
            return 301, {"location": hedef}, b""
        return 200, {"content-type": "application/pdf"}, b"MADDE 1- deneme"
    s = kur(monkeypatch, yanit)
    assert ortak.pdf_al(PDF) == b"MADDE 1- deneme"
    assert [k[3] for k in s.kayit] == [PDF, hedef]


@pytest.mark.parametrize("basliklar", [
    {"location": "https://baska.example/1.pdf"}, {},
    {"location": "https://baska.example/Anasayfa/ErrorPage?code=404"},   # site dışı "bulunamadı"
])
def test_pdf_site_disina_ya_da_adressiz_yonlendirme_durur(monkeypatch, basliklar):
    s = kur(monkeypatch, lambda y, u, kw: (302, basliklar, b""))
    with pytest.raises(ortak.ErisimDurdu) as e:
        ortak.pdf_al(PDF)
    assert "yönlendirdi (HTTP 302)" in str(e.value)
    assert "https://www.mevzuat.gov.tr" in str(e.value)
    assert len(s.kayit) == 1                               # site dışına istek gitmez


@pytest.mark.parametrize("cagri, durum, tur, govde", [
    (lambda: mevzuat.ara("borçlar"), 500, "text/html", b"<html>Hata</html>"),
    (lambda: mevzuat.ara("borçlar"), 404, "text/html", b"<html>Yok</html>"),
    (lambda: mevzuat.ara("borçlar"), 502, "application/json", b"{}"),
    (lambda: mevzuat.tam_metin("TBK"), 503, "text/html", b"<html>Bakim</html>"),
])
def test_diger_http_hatalari_kisa_turkce_bekleme_yok(monkeypatch, cagri, durum, tur, govde):
    s = kur(monkeypatch, lambda y, u, kw: (durum, {"content-type": tur}, govde))
    for _ in range(2):                                     # bekleme yok: ikinci çağrı da gider
        with pytest.raises(ortak.KaynakHatasi) as e:
            cagri()
        mesaj = str(e.value)
        assert not isinstance(e.value, ortak.ErisimDurdu)
        assert mesaj.startswith("mevzuat.gov.tr ") and f"(HTTP {durum}" in mesaj
        assert "Resmî site: https://www.mevzuat.gov.tr" in mesaj and "error" not in mesaj.lower()
    assert len(s.kayit) == 2


@pytest.mark.parametrize("hata, parca", [
    (httpx.ReadTimeout("timed out"), "zaman aşımı"),
    (httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED]"), "ağ hatası"),
])
def test_ag_hatasi_kisa_turkce_bekleme_yok(monkeypatch, hata, parca):
    def yanit(yontem, url, kw):
        raise hata
    s = kur(monkeypatch, yanit)
    for _ in range(2):
        with pytest.raises(ortak.KaynakHatasi) as e:
            mevzuat.madde("TBK", 49)
        assert str(e.value).startswith("mevzuat.gov.tr ") and parca in str(e.value)
        assert "SSL" not in str(e.value)
    assert len(s.kayit) == 2


# --- Önbellek ve kimlik çözümü ----------------------------------------------------------

def test_tam_metin_surec_icinde_onbellekte(monkeypatch):
    s = kur(monkeypatch, lambda y, u, kw: (200, {"content-type": "application/pdf"},
                                           b"MADDE 49- Kusurlu ve hukuka aykiri\nMADDE 50- x"))
    m1 = mevzuat.madde("TBK", 49)
    m2 = mevzuat.madde("6098", 50)
    assert m1["metin"].startswith("MADDE 49") and m2["metin"].startswith("MADDE 50")
    assert len(s.kayit) == 1


def test_tertip_5_disindaki_kanunlar():
    assert registry.cozumle("FSEK")[0] == "1.3.5846"
    assert registry.cozumle("5846")[0] == "1.3.5846"
    assert registry.cozumle("İİK")[0] == "1.3.2004"
    assert registry.cozumle("VUK")[0] == "1.4.213"
    assert registry.cozumle("GVK")[0] == "1.4.193"
    assert registry.cozumle("TBK")[0] == "1.5.6098"
    assert registry.cozumle("1.5.5846")[0] == "1.5.5846"          # açık kimliğe dokunulmaz
    fsek = next(x for x in registry.liste() if x["kisaltma"] == "FSEK")
    assert fsek["mevzuat_id"] == "1.3.5846"


# --- Metin kuralları ------------------------------------------------------------------

def test_bulunamayan_madde_uyarisi(monkeypatch):
    kur(monkeypatch, lambda y, u, kw: (200, {"content-type": "application/pdf"},
                                       b"MADDE 1- x\nMADDE 2- y"))
    sonuc = mevzuat.madde("TBK", 999)
    assert sonuc["metin"] is None
    assert sonuc["uyari"].startswith("m.999 metinde bulunamadı. Numara yanlış olabilir")


def test_model_ve_kullanici_metinlerinde_uzun_tire_yok():
    kok = Path(__file__).resolve().parent.parent
    dosyalar = [*sorted((kok / "turk_hukuku_mevzuat").glob("*.py")),
                kok / "README.md", kok / "PRIVACY.md", kok / "SORUMLULUK-REDDI.md"]
    bulunan = [f"{d.name}:{no}" for d in dosyalar
               for no, satir in enumerate(d.read_text(encoding="utf-8").splitlines(), 1)
               if chr(0x2014) in satir or chr(0x2013) in satir]      # uzun ve orta tire
    assert bulunan == []
