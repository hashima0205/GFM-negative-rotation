#!/usr/bin/env python3
"""Draw the implemented Droop/VSM controllers (no simulation required).

Run from any directory:
    python scripts/control_diagrams.py
    python scripts/control_diagrams.py --output outputs/control_diagrams

Requires only matplotlib. Produces editable SVG, vector PDF and 240 dpi PNG.
Source: src/dynamics.jl (machine and rhs!), inputs/common.toml.
The diagrams show one inverter; parameters remain symbolic. P/Q are measured
at Vc, Ig, not at the terminal bus. nu is per-unit frequency deviation.
The shared inner-control diagram uses the present Rvirt = Xvirt = 0 setting.
No transfer function here represents an additional simulated state: in
particular D2*s/(s+omega_D) is the zero-state transfer function of the
z realization shown beside it; nonzero initial states must be retained.
"""
from pathlib import Path
import argparse
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyArrowPatch

INK = "#203042"
BLUE = "#eaf2fb"
ORANGE = "#fff1df"


def canvas(title, height=8):
    fig, ax = plt.subplots(figsize=(16, height))
    fig.subplots_adjust(left=.025, right=.985, bottom=.04, top=.94)
    ax.set(xlim=(0, 16), ylim=(0, height))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.text(.2, height-.25, title, fontsize=19, weight="bold", color=INK)
    return fig, ax


def label(ax, x, y, text, size=13, **kwargs):
    return ax.text(x, y, text, fontsize=size, ha="center", va="center",
                   color=INK, **kwargs)


def box(ax, x, y, w, h, text, color=BLUE, size=14):
    ax.add_patch(Rectangle((x-w/2, y-h/2), w, h, facecolor=color,
                           edgecolor=INK, linewidth=1.3))
    label(ax, x, y, text, size)


def wire(ax, points, text=None, at=None):
    for a, b in zip(points[:-2], points[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=INK, lw=1.3)
    ax.add_patch(FancyArrowPatch(points[-2], points[-1], arrowstyle="-|>",
                                mutation_scale=12, color=INK, lw=1.3))
    if text:
        if at is None:
            a, b = points[-2:]
            at = ((a[0]+b[0])/2, (a[1]+b[1])/2+.25)
        label(ax, *at, text)


def node(ax, x, y):
    ax.plot(x, y, "o", color=INK, ms=4)


def summer(ax, x, y):
    ax.add_patch(Circle((x, y), .25, facecolor="white", edgecolor=INK, lw=1.3))
    label(ax, x, y, r"$\Sigma$", 15)


def reactive(ax):
    label(ax, 2.2, 3.55, "Shared reactive-power / voltage law", 14, weight="bold")
    wire(ax, [(.6, 2.7), (1.5, 2.7)], r"$Q$")
    box(ax, 2.4, 2.7, 1.8, .85, r"$\frac{1}{1+\tau_q s}$", size=20)
    wire(ax, [(3.3, 2.7), (4.55, 2.7)], r"$Q_f$")
    summer(ax, 4.8, 2.7)
    label(ax, 4.4, 2.95, "+", 12)
    wire(ax, [(4.8, 1.45), (4.8, 2.45)])
    label(ax, 4.8, 1.2, r"$Q^*$")
    label(ax, 5.05, 2.3, "−", 14)
    wire(ax, [(5.05, 2.7), (6, 2.7)])
    box(ax, 6.75, 2.7, 1.5, .85, r"$K_q$", size=18)
    wire(ax, [(7.5, 2.7), (8.55, 2.7)])
    summer(ax, 8.8, 2.7)
    label(ax, 8.4, 2.95, "−", 14)
    wire(ax, [(8.8, 1.45), (8.8, 2.45)])
    label(ax, 8.8, 1.2, r"$V_{\rm set}$")
    label(ax, 9.06, 2.3, "+", 12)
    wire(ax, [(9.05, 2.7), (11.2, 2.7)], r"$V^*$")
    box(ax, 13, 2.7, 3.6, 1.0, "Shared inner control\n(see separate diagram)", size=12)


def outer(kind):
    fig, ax = canvas(f"{kind}: outer control of one GFM inverter", 9)
    y = 6.7
    if kind == "Droop":
        wire(ax, [(.5, y), (1.3, y)], r"$P$")
        box(ax, 2.25, y, 1.9, 1, r"$\frac{1}{1+\tau_p s}$", size=21)
        wire(ax, [(3.2, y), (4.45, y)], r"$P_f$")
        summer(ax, 4.7, y)
        label(ax, 4.3, y+.28, "−", 14)
        wire(ax, [(4.7, y+1.05), (4.7, y+.25)])
        label(ax, 4.7, y+1.3, r"$P^*$")
        label(ax, 5, y+.45, "+", 12)
        wire(ax, [(4.95, y), (6.1, y)])
        box(ax, 6.85, y, 1.5, 1, r"$m_p$", size=20)
        wire(ax, [(7.6, y), (9.2, y)], r"$\nu$")
        box(ax, 10.1, y, 1.8, 1, r"$\frac{\omega_0}{s}$", size=24)
        wire(ax, [(11, y), (13.4, y)], r"$\delta$")
        label(ax, 8, 4.75,
              r"$\tau_p\dot P_f=P-P_f,\quad \nu=m_p(P^*-P_f),\quad \dot\delta=\omega_0\nu$", 17)
    else:
        summer(ax, 4.1, y)
        wire(ax, [(1.1, y), (3.85, y)], r"$P^*$")
        label(ax, 3.7, y+.3, "+", 12)
        wire(ax, [(4.1, 8), (4.1, y+.25)])
        label(ax, 4.1, 8.25, r"$P$")
        label(ax, 4.4, y+.45, "−", 14)
        wire(ax, [(4.35, y), (5.4, y)])
        box(ax, 6.35, y, 1.9, 1, r"$\frac{1}{2Hs}$", size=23)
        wire(ax, [(7.3, y), (10, y)], r"$\nu$", at=(8.3, y+.3))
        node(ax, 9.3, y)
        box(ax, 10.9, y, 1.8, 1, r"$\frac{\omega_0}{s}$", size=24)
        wire(ax, [(11.8, y), (14.7, y)], r"$\delta$")
        wire(ax, [(9.3, y), (9.3, 5.2), (7.9, 5.2)])
        node(ax, 9.3, 5.2)
        box(ax, 6.6, 5.2, 2.6, .8, r"$1/m_p+D_1$", color=ORANGE, size=17)
        wire(ax, [(5.3, 5.2), (4.1, 5.2), (4.1, y-.25)])
        label(ax, 3.8, y-.48, "−", 14)
        wire(ax, [(9.3, 5.2), (9.3, 4.05), (7.9, 4.05)])
        box(ax, 6.6, 4.05, 2.6, .8, r"$\frac{D_2s}{s+\omega_D}$", color=ORANGE, size=21)
        wire(ax, [(5.3, 4.05), (3.1, 4.05), (3.1, 6.25), (3.92, 6.53)])
        label(ax, 3.55, 6.1, "−", 14)
        label(ax, 12.3, 4.75, r"$\dot z=\omega_D(\nu-z)$"+"\n"+r"$P_{\rm wash}=D_2(\nu-z)$", 15)
    reactive(ax)
    label(ax, 8, .48,
          r"$P+jQ=V_C I_g^*,\quad \nu=(\omega-\omega_0)/\omega_0,\quad \omega_0=2\pi f_0$"
          "\n"+r"$\delta$: internal angle relative to the fixed slack frame; $\delta(0)$ is retained.", 13)
    return fig


def inner():
    fig, ax = canvas("Shared voltage / current control and electrical plant", 10)
    box(ax, 1.7, 7.8, 2.7, 1.1, r"$\mathbf{e}^*=(V^*,0)$"+"\n"+r"$R_{\rm virt}=X_{\rm virt}=0$", size=13)
    wire(ax, [(3.05, 7.8), (3.65, 7.8)])
    summer(ax, 3.9, 7.8)
    label(ax, 3.5, 8.1, "+", 12)
    wire(ax, [(4.15, 7.8), (4.7, 7.8)], r"$\mathbf{e}_v$", at=(4.4, 8.15))
    box(ax, 6.2, 7.8, 3, 1.35,
        "Voltage PI + feedforward\n"+r"$\mathbf{u}_i=G_v(s)\mathbf{e}_v$"+"\n"+r"$+F_v\mathbf{i}_g+F_{vc}C J\mathbf{v}_c$", size=12)
    wire(ax, [(7.7, 7.8), (8.3, 7.8)])
    box(ax, 9.55, 7.8, 2.5, 1.35,
        "Circular command limiter\n"+r"$\mathbf{i}_f^*=\alpha\mathbf{u}_i$"+"\n"+r"$\alpha=\min(1,\frac{I_{\max}}{\sqrt{\|\mathbf{u}_i\|^2+\epsilon}})$", color=ORANGE, size=12)
    wire(ax, [(10.8, 7.8), (11.45, 7.8)])
    summer(ax, 11.7, 7.8)
    label(ax, 11.3, 8.1, "+", 12)
    wire(ax, [(11.95, 7.8), (12.55, 7.8)], r"$\mathbf{e}_i$", at=(12.25, 8.15))
    box(ax, 14, 7.8, 2.9, 1.35,
        "Current PI + feedforward\n"+r"$\mathbf{v}_i=G_i(s)\mathbf{e}_i$"+"\n"+r"$+F_i\mathbf{v}_c+F_{ic}L_fJ\mathbf{i}_f$", size=12)
    wire(ax, [(14, 7.125), (14, 5.55)])
    box(ax, 14, 4.8, 2.9, 1.5, "LCL circuit + network\n"+r"$\mathbf{v}_c,\ \mathbf{i}_f,\ \mathbf{i}_g$"+"\n(fixed slack frame)", size=13)
    label(ax, 15.1, 6.35, r"$e^{j\delta}$", 15)
    wire(ax, [(12.55, 4.8), (10.4, 4.8)])
    box(ax, 9.2, 4.8, 2.4, 1.15, "Local-frame transform\n"+r"$e^{-j\delta}$", size=13)
    wire(ax, [(8, 4.8), (7.3, 4.8), (7.3, 5.8), (3.9, 5.8), (3.9, 7.55)])
    label(ax, 3.6, 7.3, "−", 14)
    label(ax, 5.5, 6.05, r"$\mathbf{v}_c$", 14)
    wire(ax, [(9.2, 5.375), (9.2, 5.9), (11.7, 5.9), (11.7, 7.55)])
    label(ax, 11.4, 7.3, "−", 14)
    label(ax, 10.2, 6.13, r"$\mathbf{i}_f$", 14)
    label(ax, 8, 3.05,
          r"$G_v(s)=K_{pv}+K_{iv}/s,\quad G_i(s)=K_{pi}+K_{ii}/s,\quad J(v_d,v_q)=(-v_q,v_d)$", 17)
    label(ax, 8, 2.05,
          r"$P+jQ=V_C I_g^*\ \longrightarrow\ $ outer control $\ \longrightarrow\ (V^*,\delta)$", 16)
    label(ax, 8, .85,
          "Bold symbols are local d/q vectors except at the electrical plant. Feedforward inputs are shown in block equations.\n"
          "PI integrators use the indicated errors without an added anti-windup loop. The limiter acts on the current command.\n"
          "The electrical plant retains LCL dynamics; it is not an ideal voltage source or a PWM switching model.", 12)
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).resolve().parents[1]/"outputs/control_diagrams")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "mathtext.fontset": "dejavusans",
                         "svg.fonttype": "none", "pdf.fonttype": 42})
    for name, draw in [("droop_control", lambda: outer("Droop")),
                       ("vsm_control", lambda: outer("VSM")),
                       ("shared_inner_control", inner)]:
        fig = draw()
        for extension in ("png", "pdf", "svg"):
            path = args.output/f"{name}.{extension}"
            fig.savefig(path, dpi=240, facecolor="white", bbox_inches="tight", pad_inches=.15)
            print(path)
        plt.close(fig)


if __name__ == "__main__":
    main()
