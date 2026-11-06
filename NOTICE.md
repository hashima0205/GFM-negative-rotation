# Source attribution

The VSM implementation and diagram geometry derive from
[hashima0205/VSM_decelaration](https://github.com/hashima0205/VSM_decelaration),
code commit `584b7519d67adb135404b9b319445ca428ded413`.
The remote documentation revision checked for this release is
`e8fe0e535bee84b824f58cd89139467f027c14dc`; the intervening changes affect only README.md.

The Droop equations, inputs and reference results were supplied in the verified
`droop_transfer` handoff. Their original execution tree had no Git commit.
The related public repository is
[hashima0205/gfm-deceleration-simulation](https://github.com/hashima0205/gfm-deceleration-simulation),
but its commit `22a1581b7e3807ab7edcd332e9210e1301597258` is not claimed to be the
execution commit of those saved results. File hashes identify the supplied sources.

The LCL filter, dq transformations, PI-controller equations and DroopOuter originate
from [JuliaEnergy/PowerDynamics.jl](https://github.com/JuliaEnergy/PowerDynamics.jl),
version 4.4.0, registered source tree `b2c2d56c664c475b4dbb19280b8420c5b0d68f30`.
The supplied source includes the explicitly recorded 60 Hz nominal-frequency change.
PowerDynamics copyright and license notices are retained in
[LICENSES/PowerDynamics.txt](LICENSES/PowerDynamics.txt).

The current implementation solves the linear network constraints exactly and
uses an explicit P-measurement-filter Droop path or a VSM swing-equation path.
Source references, coefficient mapping and numerical migration checks are in
[provenance](provenance/) and [docs/VALIDATION.md](docs/VALIDATION.md).
