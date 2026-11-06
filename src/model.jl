module GFMModel
using LinearAlgebra, DelimitedFiles, TOML
export Config, Stage, rhs!, voltages, measurements, legacy_to_native, native_to_legacy,
       BUS, DYN66, ALG66, load_config, make_stage, jacobian, equilibrium, spectrum, STUDY, REMOTE, SLACK, BRANCHES, NONSLACK, stateindices, frequency_base, internal_frequency

const STUDY = TOML.parsefile(joinpath(@__DIR__,"../inputs/study.toml"))
const BUS = Int.(STUDY["network"]["gfm_buses"])
const REMOTE = Int.(STUDY["network"]["remote_buses"])
const DYN66 = vcat(collect(3:15),collect(18:30),collect(33:45),collect(54:66))
const ALG66 = setdiff(1:66,DYN66)
const BASE66 = [0,15,30,51]
const BRANCHES = [Tuple(Int.(p)) for p in STUDY["network"]["branches"]]
const SLACK = Int(STUDY["network"]["slack_bus"])
const NONSLACK = setdiff(collect(1:maximum(maximum.(BRANCHES))),[SLACK])
const STATE_OFFSETS = Dict(:ig_i=>3,:ig_r=>4,:vc_i=>5,:vc_r=>6,:if_i=>7,:if_r=>8,:Qf=>11,:frequency=>12,:angle=>13)
stateindices(field;remote=false) = [13(j-1)+STATE_OFFSETS[field] for (j,b) in enumerate(BUS) if !remote || b in REMOTE]
frequency_base(c) = round(c.machines[1].w0/(2pi);digits=12)
internal_frequency(y,c,j) = frequency_base(c)*(c.control=="VSM" ? y[13(j-1)+12] : c.mp*(c.machines[j].Pset-y[13(j-1)+12]))


const MACHINE_KEYS = ["droop₊Vset", "droop₊ω0", "droop₊Kq", "droop₊τ_q", "droop₊Pset", "droop₊Qset", "vsrc₊Rf", "vsrc₊Lf", "vsrc₊C", "vsrc₊Rg", "vsrc₊Lg", "vsrc₊ω0", "vsrc₊I_max", "vsrc₊CC1_KP", "vsrc₊CC1_KI", "vsrc₊CC1_F", "vsrc₊CC1_Fcoupl", "vsrc₊VC_KP", "vsrc₊VC_KI", "vsrc₊VC_F", "vsrc₊VC_Fcoupl", "vsrc₊R_virt", "vsrc₊X_virt", "vsrc₊filter₊connected"]
struct Machine
    Vset::Float64
    w0::Float64
    Kq::Float64
    tauq::Float64
    Pset::Float64
    Qset::Float64
    Rf::Float64
    Lf::Float64
    C::Float64
    Rg::Float64
    Lg::Float64
    wf::Float64
    Imax::Float64
    cckp::Float64
    ccki::Float64
    ccf::Float64
    ccfc::Float64
    vckp::Float64
    vcki::Float64
    vcf::Float64
    vcfc::Float64
    Rv::Float64
    Xv::Float64
    connected::Float64
end
Machine(d::AbstractDict)=Machine((Float64(d[k]) for k in MACHINE_KEYS)...)

struct Config
    control::String
    mp::Float64
    taup::Float64
    H::Float64
    D1::Float64
    D2::Float64
    wd::Float64
    machines::Vector{Machine}
    lines::Matrix{Float64}
    G::Float64
    B::Float64
    faultG::Float64
    fault_on::Float64
    clearing::Float64
end

function load_config(path,case)
    a=TOML.parsefile(path)
    machines=Machine.(a["machines"])
    @assert all(m.connected==1 && m.w0==m.wf for m in machines)
    lines=reduce(vcat,permutedims.(a["lines"]))
    control=String(case["control"])
    @assert control in ["Droop","VSM"]
    mp=parse(Float64,case["mp"])
    h=control=="VSM" ? parse(Float64,case["H"]) : NaN
    tau=control=="Droop" ? parse(Float64,case["taup"]) : 2h*mp
    wd=control=="VSM" ? parse(Float64,case["omega_d"]) : 0.0
    d1=parse(Float64,case["D1"]);d2=parse(Float64,case["D2"])
    @assert mp>0 && tau>0 && (control=="Droop" || h>0) && d1>=0 && d2>=0
    Config(control,mp,tau,h,d1,d2,wd,machines,lines,
           a["G"],a["B"],a["fault_G"],a["fault_on"],a["clearing"])
end

include("network.jl")
include("dynamics.jl")
include("equilibria.jl")
end
