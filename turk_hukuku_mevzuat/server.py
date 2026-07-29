"""turk-hukuku-mevzuat MCP sunucusu.

Türk mevzuatının resmî güncel metnini (mevzuat.gov.tr) yapay zekâ aracına açar.
Amaç: model "TBK m.49" gibi bir atıf yaparken metni hafızadan değil, **resmî
kaynaktan** alıp doğrulanabilir biçimde aktarsın.

Çalıştırma:  python -m turk_hukuku_mevzuat   (ya da `turk-hukuku-mevzuat` komutu)
Taşıma:      stdio (Claude Code / Codex / Gemini CLI ile uyumlu)
"""
from __future__ import annotations

from functools import partial

import anyio
from mcp.server.fastmcp import FastMCP

from . import mevzuat, registry

mcp = FastMCP("turk-hukuku-mevzuat")


# FastMCP senkron araçları event loop üzerinde çalıştırır; bloklayan HTTP
# çağrısı tüm sunucuyu kilitler, bu yüzden işi worker thread'e taşıyoruz.
@mcp.tool()
async def madde_getir(kanun: str, madde_no: int) -> dict:
    """Bir kanunun belirli maddesinin RESMÎ güncel metnini getirir.

    Atıf yapmadan önce bunu çağır: dönen `metin` mevzuat.gov.tr'nin yürürlükteki
    konsolide metnidir; `kaynak` doğrulama URL'sidir. `metin` None ise madde
    bulunamamıştır (numara yanlış ya da mülga) — uydurma, `uyari`yı aktar.

    kanun: kısaltma ("TBK"), numara ("6098") veya tam kimlik ("1.5.6098").
    """
    return await anyio.to_thread.run_sync(partial(mevzuat.madde, kanun, madde_no))


@mcp.tool()
async def kanun_metni_getir(kanun: str) -> dict:
    """Bir kanunun RESMÎ güncel tam metnini getirir (mevzuat.gov.tr).

    Büyük kanunlar uzundur; tek madde gerekiyorsa `madde_getir` tercih edilmeli.
    Dönen: {kanun, mevzuat_id, kaynak, uzunluk, metin}.

    kanun: kısaltma ("TMK"), numara ("4721") veya tam kimlik ("1.5.4721").
    """
    return await anyio.to_thread.run_sync(partial(mevzuat.tam_metin, kanun))


@mcp.tool()
async def mevzuat_ara(ifade: str, nerede: str = "Baslik", adet: int = 10) -> dict:
    """mevzuat.gov.tr'de KANUN arar; eşleşen kanunları ve kimliklerini döndürür.

    Kanunun numarasını bilmiyorsan önce bunu çağır: dönen her sonucun `mevzuat_id`
    değeri doğrudan `madde_getir`/`kanun_metni_getir`'e verilebilir.

    nerede: "Baslik" (kanun adında ara — kanunu bulmak için), "Icerik" (tam metinde
    ara — bir kavramın hangi kanunlarda geçtiğini taramak için) ya da "Tumu".
    adet: en çok kaç sonuç (1-50).
    """
    return await anyio.to_thread.run_sync(
        partial(mevzuat.ara, ifade, nerede=nerede, adet=adet)
    )


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
