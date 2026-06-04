"""turk-hukuku-mevzuat MCP sunucusu.

Türk mevzuatının resmî güncel metnini (mevzuat.gov.tr) yapay zekâ aracına açar.
Amaç: model "TBK m.49" gibi bir atıf yaparken metni hafızadan değil, **resmî
kaynaktan** alıp doğrulanabilir biçimde aktarsın.

Çalıştırma:  python -m turk_hukuku_mevzuat   (ya da `turk-hukuku-mevzuat` komutu)
Taşıma:      stdio (Claude Code / Codex / Gemini CLI ile uyumlu)
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from . import mevzuat, registry

mcp = FastMCP("turk-hukuku-mevzuat")


@mcp.tool()
def madde_getir(kanun: str, madde_no: int) -> dict:
    """Bir kanunun belirli maddesinin RESMÎ güncel metnini getirir.

    Atıf yapmadan önce bunu çağır: dönen `metin` mevzuat.gov.tr'nin yürürlükteki
    konsolide metnidir; `kaynak` doğrulama URL'sidir. `metin` None ise madde
    bulunamamıştır (numara yanlış ya da mülga) — uydurma, `uyari`yı aktar.

    kanun: kısaltma ("TBK"), numara ("6098") veya tam kimlik ("1.5.6098").
    """
    return mevzuat.madde(kanun, madde_no)


@mcp.tool()
def kanun_metni_getir(kanun: str) -> dict:
    """Bir kanunun RESMÎ güncel tam metnini getirir (mevzuat.gov.tr).

    Büyük kanunlar uzundur; tek madde gerekiyorsa `madde_getir` tercih edilmeli.
    Dönen: {kanun, mevzuat_id, kaynak, uzunluk, metin}.

    kanun: kısaltma ("TMK"), numara ("4721") veya tam kimlik ("1.5.4721").
    """
    return mevzuat.tam_metin(kanun)


@mcp.tool()
def bilinen_kanunlar() -> list[dict]:
    """Kayıtlı kanunları (kısaltma, no, ad, mevzuat_id) listeler.

    Kayıtta olmayan kanunlar da numara/kimlikle çağrılabilir; bu yalnızca
    yaygın kanunların hızlı dizinidir.
    """
    return registry.liste()


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
