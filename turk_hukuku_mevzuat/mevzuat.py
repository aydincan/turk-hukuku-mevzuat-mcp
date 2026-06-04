"""mevzuat.gov.tr istemcisi: resmî güncel tam metni çeker, madde ayıklar.

Veri kaynağı: https://www.mevzuat.gov.tr/MevzuatMetin/<id>.pdf (Cumhurbaşkanlığı
Mevzuat Bilgi Sistemi). Tam metin PDF olarak alınır, metne dönüştürülür ve istenen
madde regex ile ayıklanır. Çekilen metin süreç boyunca önbellekte tutulur.
"""
from __future__ import annotations

import io
import re

import httpx
from pypdf import PdfReader

from . import registry

_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_BASE = "https://www.mevzuat.gov.tr/MevzuatMetin"

# basit süreç-içi önbellek: mevzuat_id -> tam metin
_CACHE: dict[str, str] = {}


def _pdf_to_text(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n".join((p.extract_text() or "") for p in reader.pages)


def tam_metin(kanun: str) -> dict:
    """Kanunun resmî güncel tam metnini döndürür.

    Dönen: {kanun, mevzuat_id, kaynak, uzunluk, metin}
    """
    mevzuat_id, ad, _ = registry.cozumle(kanun)
    kaynak = f"{_BASE}/{mevzuat_id}.pdf"
    if mevzuat_id not in _CACHE:
        r = httpx.get(kaynak, headers={"User-Agent": _UA}, timeout=60,
                      follow_redirects=True)
        if r.status_code != 200 or "pdf" not in r.headers.get("content-type", ""):
            raise LookupError(
                f"{ad} ({mevzuat_id}) için resmî metin bulunamadı (HTTP {r.status_code}). "
                f"Kimlik yanlış olabilir; açık kimlik (ör. 1.5.6098) deneyin."
            )
        _CACHE[mevzuat_id] = _pdf_to_text(r.content)
    metin = _CACHE[mevzuat_id]
    return {"kanun": ad, "mevzuat_id": mevzuat_id, "kaynak": kaynak,
            "uzunluk": len(metin), "metin": metin}


def _madde_ayikla(metin: str, no: int) -> str | None:
    bas = re.search(rf"(?im)^\s*(?:MADDE|Madde)\s*0*{no}\b", metin)
    if not bas:
        return None
    kalan = metin[bas.start() + 1:]
    son = re.search(rf"(?im)^\s*(?:MADDE|Madde)\s*0*{no + 1}\b", kalan)
    bitis = bas.start() + 1 + son.start() if son else bas.start() + 2500
    return re.sub(r"[ \t]+", " ", metin[bas.start():bitis]).strip()


def madde(kanun: str, madde_no: int) -> dict:
    """Bir kanunun belirli maddesinin resmî güncel metnini döndürür.

    Dönen: {kanun, madde_no, mevzuat_id, kaynak, metin, atif}
    `metin` None ise madde bulunamamıştır (numara yanlış ya da mülga olabilir).
    """
    tm = tam_metin(kanun)
    m = _madde_ayikla(tm["metin"], madde_no)
    return {
        "kanun": tm["kanun"],
        "madde_no": madde_no,
        "mevzuat_id": tm["mevzuat_id"],
        "kaynak": tm["kaynak"],
        "metin": m,
        "atif": f"{tm['kanun']} m.{madde_no} (kaynak: {tm['kaynak']})",
        "uyari": None if m else (
            f"m.{madde_no} metinde bulunamadı — numara yanlış olabilir ya da madde "
            f"mülga/değişik olabilir. Kaynağı elle kontrol edin: {tm['kaynak']}"
        ),
    }
