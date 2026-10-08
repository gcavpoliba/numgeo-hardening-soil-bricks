![numgeoACT](./docs/assets/numgeo-hs-logo.png)

# numgeo-hardening-soil-bricks (Fork GUI v2)

Hardening Soil (Matsuoka-Nakai, Bricks) — a standalone Fortran implementation of the Hardening
Soil model with a Matsuoka–Nakai failure surface and the BRICK small-strain stiffness extension
(Cudny & Truty 2020), extracted from [numgeo](https://www.numgeo.de/) and packaged three ways:
an [incrementalDriver](https://j-machacek.github.io/numgeo-hardening-soil-bricks/components/incremental-driver.html)
build for element tests, a standalone
[calibration tool](https://j-machacek.github.io/numgeo-hardening-soil-bricks/components/calibration.html)
for the internal constants `alpha`/`Hpp`, and a minimal
[UMAT interface](https://j-machacek.github.io/numgeo-hardening-soil-bricks/components/umat.html)
for Abaqus.

This fork modernizes the **Python/PyQt6 GUI** (`gui_hs_bricks.py`) to:

1. **Fix the diagram refresh bug** — every new simulation now resets and
   redraws all plots, tables and the amplitude combo. No stale plots from
   previous runs remain on screen.
2. **Add the TX-CIU test** (Consolidated Isotropic Undrained) using the
   driver keyword `*TriaxialUEq` (Roscoe path, `eps_v = 0` enforced). The
   GUI computes the excess pore pressure `∆u = (p0 + q/3) - p'` and plots
   the effective vs total stress path in the `q - p` plane.
3. **Add the TX-CID test** (Consolidated Isotropic Drained) using the
   driver keyword `*TriaxialE1` (renamed from the previous "TX-CD" to align
   with the standard geotechnical lab notation).
4. **Re-label the cyclic test** as **Ciclico Non Drenato per G/G0** — it uses
   `*CirculatingLoad` with `*Cartesian` (shear strain in the `xy`
   component), which is intrinsically undrained on the shear component.

The full documentation lives in `docs/`. See `docs/gui.md` for the GUI
reference, `examples/IncrementalDriver/undrained_examples/` for a ready-to-run
TX-CIU example, and `examples/IncrementalDriver/cyclic_undrained/` for the
cyclic undrained example.

Developed by Jan Machaček, Leonardo José Cocco and Marcin Cudny for numgeo.
GUI improvements by the gcavpoliba fork.
