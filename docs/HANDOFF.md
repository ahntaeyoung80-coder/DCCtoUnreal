# Handoff

## Current status

The user is building `/Game/Materials/Master/MM_MasterSurface` in Unreal 5.8.3. The last shared graph showed an error on `NormalTexture`.

## Decisions

- Import priority: ORM → Substance PBR → Blender images → Blender scalars → defaults.
- Select texture or scalar with Static Switches; do not multiply them. Current ORM wiring is R=AO, G=Roughness, B=Metallic; confirm against the export convention.

## Next

Create a read-only Unreal Editor script to export a graph report. Verify pin-connection extraction, then check the Normal default and compile status. See `docs/WORK_LOG.md` for the cumulative log.
