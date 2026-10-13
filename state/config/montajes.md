# Montajes de los discos de datos (2026-10-13, RBK 05)

| Rol | Etiqueta | Disco (by-id) | Serie | UUID ext4 | Montaje |
|---|---|---|---|---|---|
| Paridad | `parity` | `ata-WDC_WD10JPVX-60JC3T1_WD-WXU1EB6APMW5` | WD-WXU1EB6APMW5 | `a31e93cf-80b6-404a-84e3-535f60c44009` | `/srv/dev-disk-by-uuid-a31e93cf-80b6-404a-84e3-535f60c44009` |
| D1 | `d1` | `ata-TOSHIBA_MK1059GSM_Y1NDFAQES` | Y1NDFAQES | `1d82d7b3-ca0f-460f-8356-23b5e46ecf79` | `/srv/dev-disk-by-uuid-1d82d7b3-ca0f-460f-8356-23b5e46ecf79` |
| D2 | `d2` | `ata-Samsung_SSD_870_QVO_1TB_S5SVNG0N868475F` | S5SVNG0N868475F | `56801884-fc00-4ec8-a648-6135b2047cde` | `/srv/dev-disk-by-uuid-56801884-fc00-4ec8-a648-6135b2047cde` |

ext4 creado por OMV (`mkfs.ext4 -b 4096 -m 0 -E lazy_itable_init=0,lazy_journal_init=0 -O quota -O 64bit`),
0 bloques reservados, 916 GB útiles cada uno. Las letras `sdX` cambian entre arranques: no se usan.
