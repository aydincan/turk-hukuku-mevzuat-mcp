# turk-hukuku-mevzuat-mcp

Türk mevzuatının **resmî güncel metnini** ([mevzuat.gov.tr](https://www.mevzuat.gov.tr) —
Cumhurbaşkanlığı Mevzuat Bilgi Sistemi) yapay zekâ araçlarına açan bir **MCP sunucusu**.

Amaç tek cümle: model bir kanun maddesine atıf yaparken metni **hafızasından değil, resmî
kaynaktan** alsın ve **doğrulanabilir** biçimde aktarsın. "TBK m.49" denildiğinde,
sunucu maddenin yürürlükteki metnini ve doğrulama bağlantısını döndürür.

> **Hukuki danışmanlık değildir.** Bu araç yalnızca resmî metne erişimi kolaylaştırır;
> yorum, içtihat değerlendirmesi ya da somut olaya uygulama içermez. Nihai metni daima
> [mevzuat.gov.tr](https://www.mevzuat.gov.tr) üzerinden teyit edin.

---

## Ne yapar

| Tool | İşlev |
|------|-------|
| `mevzuat_ara(ifade, nerede, adet)` | Kanun arar; eşleşenleri ve `mevzuat_id`'lerini döndürür |
| `madde_getir(kanun, madde_no)` | Bir kanunun belirli maddesinin resmî güncel metni + doğrulama kaynağı |
| `kanun_metni_getir(kanun)` | Bir kanunun resmî güncel **tam** metni |
| `bilinen_kanunlar()` | Kayıtlı kanunların dizini (kısaltma, no, ad, kimlik) |

`kanun` parametresi esnektir: kısaltma (`TBK`), numara (`6098`) veya tam kimlik (`1.5.6098`).
Kayıtta olmayan kanunlar da numara/kimlikle çağrılabilir.

`mevzuat_ara`'da `nerede` üç değer alır: **`Baslik`** (kanun adında ara — kanunu
bulmak için), **`Icerik`** (tam metinde ara — bir kavramın hangi kanunlarda geçtiğini
taramak için), **`Tumu`**. Dönen `mevzuat_id` doğrudan `madde_getir`'e verilebilir —
böylece numarasını bilmediğin kanunlara da erişebilirsin.

## Nasıl çalışır

mevzuat.gov.tr, her mevzuatın konsolide (güncel) metnini şu desende PDF olarak sunar:

```
https://www.mevzuat.gov.tr/MevzuatMetin/<Tür>.<Tertip>.<No>.pdf
```

Büyük kanunların tamamı `1.5.<No>` (Tür=1 Kanun, Tertip=5) desenindedir — ör. TBK için
`1.5.6098`. Sunucu bu PDF'i çeker, metne dönüştürür (`pypdf`), istenen maddeyi regex ile
ayıklar ve süreç boyunca önbellekte tutar. Tamamen yereldir; hiçbir veri toplanmaz.

Arama, sitenin `anasayfa/MevzuatDatatable` uç noktasına gider (aranan ifade UTF-8 Base64
ile kodlanır). Her sonuç `tur.tertip.no` taşıdığından, eşleşen kanunun PDF kimliği
(dolayısıyla tam metni ve maddeleri) doğrudan elde edilir.

## Kurulum

```bash
git clone https://github.com/aydincan/turk-hukuku-mevzuat-mcp
cd turk-hukuku-mevzuat-mcp
python3 -m venv .venv && .venv/bin/pip install -e .
```

### Claude Code

```bash
claude mcp add turk-hukuku-mevzuat -- /tam/yol/.venv/bin/python -m turk_hukuku_mevzuat
```

### OpenAI Codex

`~/.codex/config.toml` içine:

```toml
[mcp_servers.turk-hukuku-mevzuat]
command = "/tam/yol/.venv/bin/python"
args = ["-m", "turk_hukuku_mevzuat"]
```

### Gemini CLI

`~/.gemini/settings.json` içindeki `mcpServers` altına:

```json
"turk-hukuku-mevzuat": {
  "command": "/tam/yol/.venv/bin/python",
  "args": ["-m", "turk_hukuku_mevzuat"]
}
```

## Bilinen sınırlar

- **Yalnızca kanunlar.** Hem arama (`MevzuatTur=1`) hem metin erişimi kanunlarla sınırlıdır;
  yönetmelik/tebliğ gibi diğer mevzuat türleri ve içtihat kapsam dışıdır.
- **Arama sıralaması garanti değil.** `mevzuat_ara` ilk sonucu en alakalı yapmayabilir;
  doğru kanunu `ad`/`no`'ya bakarak seçin.
- **PDF metnine bağımlı.** Nadiren satır kırılması/birleşme olabilir; kuşkuda kaynağı açın.
- Mülga/değişik maddelerde araç metni döndüremezse uyarı verir — **madde uydurmaz.**

## Lisans

[MIT](./LICENSE) · © 2026 Aydın Can Polatkan

Veri kaynağı [mevzuat.gov.tr](https://www.mevzuat.gov.tr)'ye aittir; bu proje yalnızca
kamuya açık resmî metne erişimi kolaylaştıran bağımsız bir istemcidir.

---

*Bu çalışma, ömrünü Türk yargısına adamış babam Hâkim Vahit Polatkan'ın ebedi anısına
ithaf edilmiştir.*
