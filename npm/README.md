# turk-hukuku-mevzuat-mcp

Türk mevzuatının **resmî güncel metnini** (mevzuat.gov.tr) yapay zekâ araçlarına açan
MCP sunucusu. Bu npm paketi, PyPI'daki Python sunucusunu `uvx` ile başlatan ince bir
sarmalayıcıdır; `npx` alışkanlığındaki kullanıcılar için ek bir kapıdır.

**Gereksinim:** [uv](https://docs.astral.sh/uv/getting-started/installation/) kurulu
olmalıdır (sunucunun kendisi Python tabanlıdır).

## Kullanım

```bash
npx -y turk-hukuku-mevzuat-mcp
```

Claude Code'a eklemek için:

```bash
claude mcp add turk-hukuku-mevzuat -- npx -y turk-hukuku-mevzuat-mcp
```

uv zaten kuruluysa npm katmanına gerek yoktur; doğrudan da eklenebilir:

```bash
claude mcp add turk-hukuku-mevzuat -- uvx --from turk-hukuku-mevzuat-mcp turk-hukuku-mevzuat
```

## Araçlar

- `madde_getir` : bir kanun maddesinin resmî güncel metni
- `kanun_metni_getir` : kanunun resmî tam metni
- `mevzuat_ara` : mevzuat.gov.tr'de kanun arama
- `bilinen_kanunlar` : kayıtlı kanunların hızlı dizini

## Bağlantılar

- Site: https://turk-hukuku.com/mcp/
- Kaynak: https://github.com/aydincan/turk-hukuku-mevzuat-mcp
- PyPI: https://pypi.org/project/turk-hukuku-mevzuat-mcp/

Hukuki danışmanlık değildir; çıktılar resmî kaynağa giden doğrulama bağlantısı taşır.

<!-- mcp-name: io.github.aydincan/turk-hukuku-mevzuat-mcp -->
