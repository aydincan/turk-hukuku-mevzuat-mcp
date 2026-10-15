"""Bilinen Türk kanunları kayıt defteri ve kimlik çözümleyici.

mevzuat.gov.tr tam metni şu desende sunar:
    https://www.mevzuat.gov.tr/MevzuatMetin/<Tür>.<Tertip>.<No>.pdf
Test edilen büyük kanunların çoğu **Tür=1 (Kanun), Tertip=5** desenindedir. Bu yüzden
bilinmeyen bir kanun numarası için de varsayılan olarak `1.5.<No>` denenir; gerekirse açık
kimlik (ör. "1.5.6098") doğrudan verilebilir. Başka tertipte yayımlanan kanunlar `OZEL_ID`
ile eşlenir (ör. FSEK 1.3.5846, İİK 1.3.2004, VUK 1.4.213, GVK 1.4.193); bunların 1.5.<No>
adresi sitenin 404 sayfasına yönlenir.
"""
from __future__ import annotations

# kısaltma -> (kanun no, tam ad). Hepsi mevzuat.gov.tr'de 1.5.<no> olarak doğrulanmıştır
# ya da aynı desende sunulur. Açık ID gerektiren istisnalar `OZEL_ID` ile geçilir.
KANUNLAR: dict[str, tuple[int, str]] = {
    "TMK": (4721, "Türk Medenî Kanunu"),
    "TBK": (6098, "Türk Borçlar Kanunu"),
    "TTK": (6102, "Türk Ticaret Kanunu"),
    "TCK": (5237, "Türk Ceza Kanunu"),
    "CMK": (5271, "Ceza Muhakemesi Kanunu"),
    "HMK": (6100, "Hukuk Muhakemeleri Kanunu"),
    "İİK": (2004, "İcra ve İflas Kanunu"),
    "İŞK": (4857, "İş Kanunu"),
    "SENDİKALAR": (6356, "Sendikalar ve Toplu İş Sözleşmesi Kanunu"),
    "SGK": (5510, "Sosyal Sigortalar ve Genel Sağlık Sigortası Kanunu"),
    "İSG": (6331, "İş Sağlığı ve Güvenliği Kanunu"),
    "TKHK": (6502, "Tüketicinin Korunması Hakkında Kanun"),
    "KMK": (634, "Kat Mülkiyeti Kanunu"),
    "SMK": (6769, "Sınai Mülkiyet Kanunu"),
    "FSEK": (5846, "Fikir ve Sanat Eserleri Kanunu"),
    "REKABET": (4054, "Rekabetin Korunması Hakkında Kanun"),
    "SPK": (6362, "Sermaye Piyasası Kanunu"),
    "BANKACILIK": (5411, "Bankacılık Kanunu"),
    "KVKK": (6698, "Kişisel Verilerin Korunması Kanunu"),
    "İYUK": (2577, "İdari Yargılama Usulü Kanunu"),
    "VUK": (213, "Vergi Usul Kanunu"),
    "GVK": (193, "Gelir Vergisi Kanunu"),
    "KVK": (5520, "Kurumlar Vergisi Kanunu"),
    "KDV": (3065, "Katma Değer Vergisi Kanunu"),
    "KİK": (4734, "Kamu İhale Kanunu"),
    "KABAHATLER": (5326, "Kabahatler Kanunu"),
    "ETK": (6563, "Elektronik Ticaretin Düzenlenmesi Hakkında Kanun"),
    "YUKK": (6458, "Yabancılar ve Uluslararası Koruma Kanunu"),
    "AVUKATLIK": (1136, "Avukatlık Kanunu"),
    "ÇEVRE": (2872, "Çevre Kanunu"),
    "İMAR": (3194, "İmar Kanunu"),
    "ANAYASA": (2709, "Türkiye Cumhuriyeti Anayasası"),
    "DMK": (657, "Devlet Memurları Kanunu"),
    "İNFAZ": (5275, "Ceza ve Güvenlik Tedbirlerinin İnfazı Hakkında Kanun"),
    "HUAK": (6325, "Hukuk Uyuşmazlıklarında Arabuluculuk Kanunu"),
    "GÜMRÜK": (4458, "Gümrük Kanunu"),
}

# Tertip 5 dışında yayımlanan kanunlar: kanun no -> mevzuat.gov.tr kimliği. Hepsi Ekim
# 2026'da sitenin arama sonucundan (mevzuatTertip) alındı ve madde çekilerek doğrulandı;
# 1.5.<No> adresleri sitenin 404 sayfasına yönleniyor.
OZEL_ID: dict[int, str] = {
    5846: "1.3.5846",   # FSEK (1951)
    2004: "1.3.2004",   # İİK (1932)
    213: "1.4.213",     # VUK (1961)
    193: "1.4.193",     # GVK (1960)
}


def _kimlik(no: int) -> str:
    return OZEL_ID.get(no, f"1.5.{no}")


# Kısaltma alias'ları (kullanıcı farklı yazabilir) -> kanonik anahtar
ALIAS: dict[str, str] = {
    "MEDENİ": "TMK", "MEDENI": "TMK", "TURK MEDENI KANUNU": "TMK",
    "BORÇLAR": "TBK", "BORCLAR": "TBK", "TURK BORCLAR KANUNU": "TBK",
    "TİCARET": "TTK", "TICARET": "TTK",
    "CEZA": "TCK", "TURK CEZA KANUNU": "TCK",
    "İŞ KANUNU": "İŞK", "IS KANUNU": "İŞK", "İŞ K": "İŞK", "IS K": "İŞK",
    "TÜKETİCİ": "TKHK", "TUKETICI": "TKHK",
    "KAT MÜLKİYETİ": "KMK", "KAT MULKIYETI": "KMK",
}


def _norm(s: str) -> str:
    return s.strip().upper().replace(".", "").replace("  ", " ")


def cozumle(kanun: str) -> tuple[str, str, int | None]:
    """Girdiyi (mevzuat_id, ad, no) üçlüsüne çözer.

    Kabul edilenler:
      - Tam kimlik: "1.5.6098"
      - Kısaltma:  "TBK", "tbk", "İş Kanunu"
      - Numara:    "6098", 6098
    """
    s = str(kanun).strip()

    # 1) Tam kimlik (a.b.c)
    parts = s.split(".")
    if len(parts) == 3 and all(p.strip().isdigit() for p in parts):
        no = int(parts[2])
        ad = next((a for _, (n, a) in KANUNLAR.items() if n == no), f"Kanun No {no}")
        return s, ad, no

    # 2) Salt numara
    if s.isdigit():
        no = int(s)
        ad = next((a for _, (n, a) in KANUNLAR.items() if n == no), f"Kanun No {no}")
        return _kimlik(no), ad, no

    # 3) Kısaltma / ad
    key = _norm(s)
    key = ALIAS.get(key, key)
    if key in KANUNLAR:
        no, ad = KANUNLAR[key]
        return _kimlik(no), ad, no

    # 4) Bilinmeyen ad -> hata için None
    raise ValueError(
        f"Bilinmeyen kanun: {kanun!r}. Kısaltma (TBK), numara (6098) ya da "
        f"tam kimlik (1.5.6098) verin. Bilinenler: bilinen_kanunlar() ile listelenir."
    )


def liste() -> list[dict]:
    return [
        {"kisaltma": k, "no": no, "ad": ad, "mevzuat_id": _kimlik(no)}
        for k, (no, ad) in sorted(KANUNLAR.items())
    ]
