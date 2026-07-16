# Gizlilik Politikası — Privacy Policy

`turk-hukuku-mevzuat-mcp`, Türk mevzuatının resmî güncel metnini yapay zekâ araçlarına
açan bir **MCP sunucusudur.** Tamamen **sizin makinenizde / oturumunuzda** çalışır.

## Veri toplama: YOK

- Sunucu **hiçbir kişisel veri toplamaz, saklamaz veya proje sahibine göndermez.**
- **Telemetri, analitik, izleme yoktur.** Kaynak kodda loglama, veritabanı veya disk
  önbelleği bulunmaz; sorgular ve sonuçlar **kalıcı olarak saklanmaz.**
- Proje sahibi sizin sorgularınıza **erişemez.**

## Dışarıya giden tek bağlantı

Sunucu yalnızca tek bir resmî, kamuya açık kaynağa bağlanır:

- **`https://www.mevzuat.gov.tr`** — Cumhurbaşkanlığı Mevzuat Bilgi Sistemi (kanunun
  resmî güncel metnini PDF olarak çekmek için).

Yani çağrılarınız (örn. "TBK m.49") yalnızca bu resmî siteye iletilir; başka hiçbir
üçüncü tarafa gitmez. Bu siteye yapılan istek, mevzuat.gov.tr'nin kendi gizlilik ve
erişim koşullarına tabidir.

## Müvekkil ve kişisel veri uyarısı

Sorgu metni kanun/madde referansından ibaret olmalıdır. **Sorgularınıza müvekkil adı
veya kişisel veri koymayın**; KVKK ve meslek sırrı yükümlülükleriniz sizdedir
(bkz. [`SORUMLULUK-REDDI.md`](./SORUMLULUK-REDDI.md)).

## İletişim

Sorular için bu depoda bir **issue** açabilirsiniz.

---

**In English:** `turk-hukuku-mevzuat-mcp` is an MCP server that exposes the official,
current text of Turkish legislation to AI tools. It runs entirely **locally** on your
machine/session. It **collects, stores, or transmits no personal data**, has **no
telemetry, analytics, logging, database, or disk cache**, and the maintainer cannot
access your queries. Its **only** outbound connection is to **`https://www.mevzuat.gov.tr`**
(the official legislation database) to fetch statute text; requests there are subject to
that site's own policies. Do not put client names or personal data in your queries.
