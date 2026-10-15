# turk-hukuku-mevzuat-mcp

Türk mevzuatının **resmî güncel metnini** ([mevzuat.gov.tr](https://www.mevzuat.gov.tr),
Cumhurbaşkanlığı Mevzuat Bilgi Sistemi) yapay zekâ araçlarına açan bir **MCP sunucusu**.

Amaç tek cümle: model bir kanun maddesine atıf yaparken metni **hafızasından değil, resmî
kaynaktan** alsın ve **doğrulanabilir** biçimde aktarsın. "TBK m.49" denildiğinde,
sunucu maddenin yürürlükteki metnini ve doğrulama bağlantısını döndürür.

> **Hukuki danışmanlık değildir.** Bu araç yalnızca resmî metne erişimi kolaylaştırır;
> yorum, içtihat değerlendirmesi ya da somut olaya uygulama içermez. Nihai metni daima
> [mevzuat.gov.tr](https://www.mevzuat.gov.tr) üzerinden teyit edin.

Ayrıntı: [`SORUMLULUK-REDDI.md`](./SORUMLULUK-REDDI.md) · [`PRIVACY.md`](./PRIVACY.md) (veri toplama yok, telemetri yok; tek dış bağlantı mevzuat.gov.tr).

**Belgeler ve kurulum rehberi:** [turk-hukuku.com/mcp](https://turk-hukuku.com/mcp/) · Terminal kullanmıyorsanız [masaüstü uygulaması](https://turk-hukuku.com/uygulama/) bu sunucuyu kendisi kurup çalıştırır (Mac ve Windows).

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

`mevzuat_ara`'da `nerede` üç değer alır: **`Baslik`** (kanun adında ara: kanunu
bulmak için), **`Icerik`** (tam metinde ara: bir kavramın hangi kanunlarda geçtiğini
taramak için), **`Tumu`**. Dönen `mevzuat_id` doğrudan `madde_getir`'e verilebilir;
böylece numarasını bilmediğin kanunlara da erişebilirsin.

## Nasıl çalışır

mevzuat.gov.tr, her mevzuatın konsolide (güncel) metnini şu desende PDF olarak sunar:

```
https://www.mevzuat.gov.tr/MevzuatMetin/<Tür>.<Tertip>.<No>.pdf
```

Büyük kanunların çoğu `1.5.<No>` (Tür=1 Kanun, Tertip=5) desenindedir; ör. TBK için
`1.5.6098`. Daha eski tertipte yayımlananlar kayıtta kendi kimlikleriyle tutulur (FSEK
`1.3.5846`, İİK `1.3.2004`, VUK `1.4.213`, GVK `1.4.193`). Sunucu PDF'i çeker, metne
dönüştürür (`pypdf`), istenen maddeyi regex ile ayıklar ve süreç boyunca önbellekte tutar.
Tamamen yereldir; hiçbir veri toplanmaz.

Arama, sitenin `anasayfa/MevzuatDatatable` uç noktasına gider (aranan ifade UTF-8 Base64
ile kodlanır). Her sonuç `tur.tertip.no` taşıdığından, eşleşen kanunun PDF kimliği
(dolayısıyla tam metni ve maddeleri) doğrudan elde edilir.

## Resmî siteye saygı

- **Kendini tanıtır.** Her istekte kendi User-Agent'ını gönderir:
  `turk-hukuku-mevzuat-mcp/<sürüm> (+https://turk-hukuku.com/mcp/)`. Tarayıcı ya da resmî web
  uygulaması gibi davranmaz; bu amaçla başlık eklemez.
- **Sınırlı istek.** mevzuat.gov.tr'ye aynı anda tek istek gider ve iki istek arasında en
  az bir saniye beklenir (yaklaşık saniyede bir istek).
- **Oturum içi önbellek.** Çekilen kanun metinleri yalnızca oturum boyunca bellekte tutulur;
  aynı kanun yeniden istenince siteye tekrar gidilmez. Diske bir şey yazılmaz.
- **Captcha çözmez, atlamaz; sınırda durur.** Site doğrulama (captcha) isterse, erişimi
  reddederse (HTTP 403), erişim sınırı bildirirse (HTTP 429), beklenen veri yerine başka bir
  sayfaya ya da site dışına yönlendirirse veya bir web sayfası döndürürse sunucu durur,
  isteği yinelemez ve sizi resmî siteye yönlendirir. Siteye bir süre (yaklaşık iki dakika
  ya da sitenin bildirdiği süre kadar) yeni istek göndermez. Var olmayan bir kanun kimliği
  ise yalnızca "bulunamadı" hatası verir.
- **Geçici hatalarda kısa bir ileti verir.** Sitede geçici bir arıza (HTTP 5xx), "bulunamadı"
  yanıtı (HTTP 404) ya da ağ hatası olursa sunucu bunu kısa bir Türkçe iletiyle bildirir ve
  isteği yinelemez; bu durumda bekleme süresi uygulanmaz.

## Kurulum

[PyPI](https://pypi.org/project/turk-hukuku-mevzuat-mcp/)'de yayımlıdır; [`uv`](https://docs.astral.sh/uv/)
ile ayrı kurulum gerekmeden çalışır.

### Claude Code

```bash
claude mcp add turk-hukuku-mevzuat -- uvx --from turk-hukuku-mevzuat-mcp turk-hukuku-mevzuat
```

### OpenAI Codex

`~/.codex/config.toml` içine:

```toml
[mcp_servers.turk-hukuku-mevzuat]
command = "uvx"
args = ["--from", "turk-hukuku-mevzuat-mcp", "turk-hukuku-mevzuat"]
```

### Gemini CLI

`~/.gemini/settings.json` içindeki `mcpServers` altına:

```json
"turk-hukuku-mevzuat": {
  "command": "uvx",
  "args": ["--from", "turk-hukuku-mevzuat-mcp", "turk-hukuku-mevzuat"]
}
```

### Alternatif: pip

```bash
pip install turk-hukuku-mevzuat-mcp
# komut: turk-hukuku-mevzuat   (ya da: python -m turk_hukuku_mevzuat)
```

## Bilinen sınırlar

- **Yalnızca kanunlar.** Hem arama (`MevzuatTur=1`) hem metin erişimi kanunlarla sınırlıdır;
  yönetmelik/tebliğ gibi diğer mevzuat türleri ve içtihat kapsam dışıdır.
- **Arama sıralaması garanti değil.** `mevzuat_ara` ilk sonucu en alakalı yapmayabilir;
  doğru kanunu `ad`/`no`'ya bakarak seçin.
- **PDF metnine bağımlı.** Nadiren satır kırılması/birleşme olabilir; kuşkuda kaynağı açın.
- Mülga/değişik maddelerde araç metni döndüremezse uyarı verir; **madde uydurmaz.**

## Lisans

[MIT](./LICENSE) · © 2026 Aydın Can Polatkan

Veri kaynağı [mevzuat.gov.tr](https://www.mevzuat.gov.tr)'ye aittir; bu proje yalnızca
kamuya açık resmî metne erişimi kolaylaştıran bağımsız bir istemcidir.

---

*Bu çalışma, ömrünü Türk yargısına adamış babam Hâkim Vahit Polatkan'ın ebedi anısına
ithaf edilmiştir.*

<!-- mcp-name: io.github.aydincan/turk-hukuku-mevzuat-mcp -->
