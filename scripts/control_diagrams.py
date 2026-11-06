#!/usr/bin/env python3
"""Draw the implemented Droop/VSM controllers (no simulation required).

Run from any directory:
    python scripts/control_diagrams.py
    python scripts/control_diagrams.py --output outputs/control_diagrams

Requires only matplotlib. Produces compact monochrome 400 dpi PNG diagrams.
Source: src/dynamics.jl (machine and rhs!), inputs/common.toml.
The diagrams show one inverter; parameters remain symbolic. P/Q are measured
at Vc, Ig, not at the terminal bus. nu is per-unit frequency deviation.
The shared inner-control diagram uses the present Rvirt = Xvirt = 0 setting.
Bold signals are local dq vectors; ev=e*-vc, ei=if*-if. Feedforward
inputs are included in block equations. Limiter: alpha=min(1, Imax/
sqrt(||ui||^2+epsilon)); it limits the command, not the physical current.
P+jQ=Vc*conj(Ig), nu=(omega-omega0)/omega0, delta_dot=omega0*nu.
The fixed-slack frame rotates at omega0; transforms use relative delta.
PI integrator states and filter initial conditions are retained; no
additional anti-windup loop is present in the implementation.
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

INK = "#000000"
BLUE = "#ffffff"
ORANGE = "#ffffff"


def canvas(title, height=8):
    fig, ax = plt.subplots(figsize=(10, height/1.6))
    fig.subplots_adjust(left=.025, right=.985, bottom=.04, top=.94)
    ax.set(xlim=(0, 16), ylim=(0, height))
    ax.set_aspect("equal")
    ax.axis("off")
    ax.text(.2, height-.25, title, fontsize=12, weight="normal", color=INK)
    return fig, ax


def label(ax, x, y, text, size=11, **kwargs):
    return ax.text(x, y, text, fontsize=size, ha="center", va="center",
                   color=INK, **kwargs)


def box(ax, x, y, w, h, text, color=BLUE, size=14):
    ax.add_patch(Rectangle((x-w/2, y-h/2), w, h, facecolor=color,
                           edgecolor=INK, linewidth=.9))
    label(ax, x, y, text, size)


def wire(ax, points, text=None, at=None):
    for a, b in zip(points[:-2], points[1:-1]):
        ax.plot([a[0], b[0]], [a[1], b[1]], color=INK, lw=.9)
    ax.add_patch(FancyArrowPatch(points[-2], points[-1], arrowstyle="-|>",
                                mutation_scale=9, color=INK, lw=.9))
    if text:
        if at is None:
            a, b = points[-2:]
            at = ((a[0]+b[0])/2, (a[1]+b[1])/2+.25)
        label(ax, *at, text)


def node(ax, x, y):
    ax.plot(x, y, "o", color=INK, ms=4)


def summer(ax, x, y):
    ax.add_patch(Circle((x, y), .25, facecolor="white", edgecolor=INK, lw=.9))
    label(ax, x, y, r"$\Sigma$", 12)


def reactive(ax, y=1.35):
    wire(ax, [(.4,y),(1.15,y)], r"$Q$")
    box(ax,2,y,1.7,.7,r"$\frac{1}{1+\tau_qs}$",size=16)
    wire(ax,[(2.85,y),(4.15,y)],r"$Q_f$")
    summer(ax,4.4,y)
    label(ax,4.05,y+.28,"+",10)
    wire(ax,[(4.4,y-.8),(4.4,y-.25)])
    label(ax,4.0,y-.75,r"$Q^*$")
    label(ax,4.7,y-.35,"−",11)
    wire(ax,[(4.65,y),(5.8,y)])
    box(ax,6.5,y,1.4,.7,r"$K_q$",size=14)
    wire(ax,[(7.2,y),(8.35,y)])
    summer(ax,8.6,y)
    label(ax,8.23,y+.28,"−",11)
    wire(ax,[(8.6,y-.8),(8.6,y-.25)])
    label(ax,8.0,y-.75,r"$V_{\rm set}$")
    label(ax,8.9,y-.35,"+",10)
    wire(ax,[(8.85,y),(11.0,y)],r"$V^*$")
    box(ax,12.6,y,3.2,.8,"Voltage/current control",size=10)


def outer(kind):
    vsm=kind=="VSM"
    fig,ax=canvas(f"{kind} control",6.5 if vsm else 4.5)
    y=5.25 if vsm else 3.25
    if not vsm:
        wire(ax,[(.4,y),(1.15,y)],r"$P$")
        box(ax,2,y,1.7,.7,r"$\frac{1}{1+\tau_ps}$",size=16)
        wire(ax,[(2.85,y),(4.15,y)],r"$P_f$")
        summer(ax,4.4,y)
        label(ax,4.03,y+.28,"−",11)
        wire(ax,[(4.4,y+.75),(4.4,y+.25)])
        label(ax,3.95,y+.72,r"$P^*$")
        label(ax,4.7,y+.35,"+",10)
        wire(ax,[(4.65,y),(5.8,y)])
        box(ax,6.5,y,1.4,.7,r"$m_p$",size=14)
        wire(ax,[(7.2,y),(9.2,y)],r"$\nu$")
        box(ax,10,y,1.6,.7,r"$\frac{\omega_0}{s}$",size=18)
        wire(ax,[(10.8,y),(14.2,y)],r"$\delta$")
    else:
        summer(ax,3.8,y)
        wire(ax,[(.4,y),(3.55,y)],r"$P^*$")
        label(ax,3.43,y+.28,"+",10)
        wire(ax,[(3.8,y+.75),(3.8,y+.25)])
        label(ax,3.35,y+.72,r"$P$")
        label(ax,4.1,y+.35,"−",11)
        wire(ax,[(4.05,y),(5.4,y)])
        box(ax,6.3,y,1.8,.7,r"$\frac{1}{2Hs}$",size=18)
        wire(ax,[(7.2,y),(10,y)],r"$\nu$",at=(8.3,y+.25))
        node(ax,9.1,y)
        box(ax,10.8,y,1.6,.7,r"$\frac{\omega_0}{s}$",size=18)
        wire(ax,[(11.6,y),(14.2,y)],r"$\delta$")
        wire(ax,[(9.1,y),(9.1,4.1),(7.6,4.1)])
        node(ax,9.1,4.1)
        box(ax,6.3,4.1,2.6,.65,r"$1/m_p+D_1$",size=13)
        summer(ax,3.8,4.1)
        wire(ax,[(5,4.1),(4.05,4.1)])
        label(ax,4.18,4.36,"+",10)
        wire(ax,[(3.8,4.35),(3.8,y-.25)])
        label(ax,4.12,y-.4,"−",11)
        wire(ax,[(9.1,4.1),(9.1,3),(7.6,3)])
        box(ax,6.3,3,2.6,.75,r"$\frac{D_2s}{s+\omega_D}$",size=17)
        wire(ax,[(5,3),(3.8,3),(3.8,3.85)])
        label(ax,4.1,3.75,"+",10)
    reactive(ax)
    return fig


def inner():
    """Functional blocks only; PI, feedforward and dq transforms are internal."""
    fig,ax=canvas("Common voltage/current control",2.5)
    y=1.25
    wire(ax,[(.3,y),(1.9,y)],r"$V^*,\ \delta$")
    box(ax,3.4,y,3,.9,"Voltage controller",size=10)
    wire(ax,[(4.9,y),(6.0,y)])
    box(ax,7.4,y,2.8,.9,"Current limiter",size=10)
    wire(ax,[(8.8,y),(9.9,y)])
    box(ax,11.4,y,3,.9,"Current controller",size=10)
    wire(ax,[(12.9,y),(15.5,y)],"To LCL filter",at=(14.2,y+.33))
    return fig


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,
        default=Path(__file__).resolve().parents[1]/"outputs/control_diagrams")
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    plt.rcParams.update({"font.family":"DejaVu Serif","mathtext.fontset":"dejavuserif"})
    for name,draw in [("droop_control",lambda:outer("Droop")),
                      ("vsm_control",lambda:outer("VSM")),
                      ("shared_inner_control",inner)]:
        fig=draw()
        path=args.output/f"{name}.png"
        fig.savefig(path,dpi=400,facecolor="white",bbox_inches="tight",pad_inches=.08)
        print(path)
        plt.close(fig)


if __name__=="__main__":
    main()
