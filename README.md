# NAS con Raspberry Pi 5

Sistema multiagéntico (plugins de Claude Code) para montar desde cero, documentar y mantener un NAS doméstico:
Raspberry Pi 5 + Radxa Penta SATA HAT, Raspberry Pi OS Lite (Trixie), OpenMediaVault 8, SnapRAID + MergerFS,
Nextcloud AIO, restic, NUT y hd-idle.

Cada rol es un plugin con skills `create` / `update` / `validate` / `approve`; los entregables se versionan en
`outputs/<entregable>/vN/` y cada rol solo arranca si el entregable anterior está aprobado.

| Plugin | Entregable |
|---|---|
| `requirements-plugin` | Requisitos del NAS (NRD) |
| `architect-plugin` | Arquitectura (HLD + ADR) |
| `runbook-plugin` | Runbooks por fase (RBK) |
| `operator-plugin` | Registro de ejecución (OPS) |
| `maintainer-plugin` | Planes de actualización (UPD) y mantenimiento (MNT) |
| `storage-plugin` | Planes de cambio de discos (DCP) |

## Versión anterior

La guía de 2020 (Raspberry Pi 4 + NextcloudPi) está en [legacy/v1/](legacy/v1/) y en el tag `v1-nextcloudpi`.

## Créditos

La estructura de plugins, skills, validadores y hooks deriva de
[Redefining Data Engineering with AI](https://github.com/RDEWAI/Redefining-DataEngineering-With-AI) (Apache 2.0).
Ver [NOTICE](NOTICE).
