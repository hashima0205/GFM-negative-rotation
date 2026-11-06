module GFMModel
using LinearAlgebra, DelimitedFiles, TOML
export Config, Stage, rhs!, voltages, measurements, legacy_to_native, native_to_legacy,
       BUS, DYN66, ALG66, load_config, make_stage, jacobian, equilibrium, spectrum

const BUS = [1,2,3,7]
const DYN66 = vcat(collect(3:15),collect(18:30),collect(33:45),collect(54:66))
const ALG66 = setdiff(1:66,DYN66)
const BASE66 = [0,15,30,51]
const BRANCHES = [(1,4),(4,6),(5,6),(3,5),(2,3),(2,5),(4,5),(2,8),(2,7),(7,8),(5,8)]
const NONSLACK = [1,2,3,4,5,7,8]

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
    @assert all(m.connected==1 && m.w0==m.wf==2pi*60 for m in machines)
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

struct Stage
    config::Config
    name::String
    Y::Matrix{ComplexF64}
    W::Matrix{ComplexF64}
    v0::Vector{ComplexF64}
end

"""Eliminate the 14 linear algebraic bus-voltage variables without a time-scale approximation."""
function make_stage(c,name)
    @assert name in ["pre","fault","post"]
    Y=zeros(ComplexF64,8,8)
    for (i,(a,b)) in enumerate(BRANCHES)
        active=(name=="post" && i==7) ? 0.0 : 1.0
        y=active/complex(c.lines[i,1],c.lines[i,2])
        Y[a,a]+=y;Y[b,b]+=y;Y[a,b]-=y;Y[b,a]-=y
    end
    Y[5,5]+=complex(c.G,c.B)
    name=="fault" && (Y[4,4]+=c.faultG)
    E=zeros(ComplexF64,7,4)
    for (j,b) in enumerate(BUS); E[findfirst(==(b),NONSLACK),j]=1;end
    W=zeros(ComplexF64,8,4);v0=zeros(ComplexF64,8);v0[6]=1
    W[NONSLACK,:]=Y[NONSLACK,NONSLACK]\E
    v0[NONSLACK]=-Y[NONSLACK,NONSLACK]\Y[NONSLACK,6]
    Stage(c,name,Y,W,v0)
end

function voltage(y,s,b)
    ur=real(s.v0[b]);ui=imag(s.v0[b])
    for j in 1:4
        k=13(j-1);w=s.W[b,j];ir=y[k+4];ii=y[k+3]
        ur+=real(w)*ir-imag(w)*ii;ui+=imag(w)*ir+real(w)*ii
    end
    complex(ur,ui)
end
voltages(y,s)=[voltage(y,s,b) for b in 1:8]

function machine(y,s,j)
    c=s.config;m=c.machines[j];k=13(j-1)
    δ=y[k+13];cs=cos(δ);sn=sin(δ)
    vc=complex(y[k+6],y[k+5]);ig=complex(y[k+4],y[k+3]);iff=complex(y[k+8],y[k+7])
    rot=complex(cs,-sn);vcdq=vc*rot;igdq=ig*rot;ifdq=iff*rot
    pcap=real(vc*conj(ig));qcap=imag(vc*conj(ig))
    vref=m.Vset-m.Kq*(y[k+11]-m.Qset)
    erefd=vref-real(igdq)*m.Rv+imag(igdq)*m.Xv
    erefq=-imag(igdq)*m.Rv-real(igdq)*m.Xv
    ed=erefd-real(vcdq);eq=erefq-imag(vcdq)
    ud=-m.vcfc*m.C*imag(vcdq)+m.vckp*ed+m.vcki*y[k+10]+m.vcf*real(igdq)
    uq= m.vcfc*m.C*real(vcdq)+m.vckp*eq+m.vcki*y[k+9]+m.vcf*imag(igdq)
    factor=min(one(ud),m.Imax/sqrt(ud^2+uq^2+1e-6))
    rd=factor*ud;rq=factor*uq
    eid=rd-real(ifdq);eiq=rq-imag(ifdq)
    vid=-m.ccfc*m.Lf*imag(ifdq)+m.cckp*eid+m.ccki*y[k+2]+m.ccf*real(vcdq)
    viq= m.ccfc*m.Lf*real(ifdq)+m.cckp*eiq+m.ccki*y[k+1]+m.ccf*imag(vcdq)
    vi=complex(vid,viq)*conj(rot)
    nu=c.control=="Droop" ? c.mp*(m.Pset-y[k+12]) : y[k+12]
    (;δ,vc,ig,iff,pcap,qcap,ed,eq,eid,eiq,ud,uq,rd,rq,factor,vi,nu)
end

"""Explicit P-filter Droop and swing-equation VSM paths; shared electrical and inner-control equations."""
function rhs!(dy,y,s,t)
    c=s.config
    for j in 1:4
        m=c.machines[j];k=13(j-1);a=machine(y,s,j);u=voltage(y,s,BUS[j]);w=m.wf
        igdot=(w/m.Lg)*(a.vc-m.connected*u-m.Rg*a.ig-im*m.Lg*a.ig)
        vcdot=(w/m.C)*(a.iff-a.ig-im*m.C*a.vc)
        ifdot=(w/m.Lf)*(a.vi-a.vc-m.Rf*a.iff-im*m.Lf*a.iff)
        dy[k+1]=a.eiq;dy[k+2]=a.eid
        dy[k+3]=imag(igdot);dy[k+4]=real(igdot)
        dy[k+5]=imag(vcdot);dy[k+6]=real(vcdot)
        dy[k+7]=imag(ifdot);dy[k+8]=real(ifdot)
        dy[k+9]=a.eq;dy[k+10]=a.ed
        dy[k+11]=(a.qcap-y[k+11])/m.tauq
        if c.control=="Droop"
            dy[k+12]=(a.pcap-y[k+12])/c.taup
        else
            dy[k+12]=(m.Pset-a.pcap-(1/c.mp+c.D1)*a.nu-c.D2*(a.nu-y[52+j]))/(2c.H)
            dy[52+j]=c.wd*(a.nu-y[52+j])
        end
        dy[k+13]=m.w0*a.nu
    end
    nothing
end

function legacy_to_native(x,c;z=zeros(4))
    y=copy(x[DYN66])
    if c.control=="VSM"
        for j in 1:4;y[13(j-1)+12]=c.mp*(c.machines[j].Pset-y[13(j-1)+12]);end
        append!(y,z)
    end
    y
end
function native_to_legacy(y,s)
    c=s.config;x=zeros(66);x[DYN66]=y[1:52];u=voltages(y,s)
    for (j,b) in enumerate(BUS)
        k=BASE66[j];x[k+1]=real(u[b]);x[k+2]=imag(u[b])
        c.control=="VSM" && (x[k+14]=c.machines[j].Pset-y[13(j-1)+12]/c.mp)
    end
    for (b,k) in [(4,46),(5,48),(8,50)];x[k]=real(u[b]);x[k+1]=imag(u[b]);end
    x
end

function measurements(y,s)
    u=voltages(y,s);c=s.config
    [merge(machine(y,s,j),(;u=u[BUS[j]],terminal=u[BUS[j]]*conj(complex(y[13(j-1)+4],y[13(j-1)+3])))) for j in 1:4]
end

function jacobian(f,x;h=1e-6)
    J=zeros(length(x),length(x));a=zeros(length(x));b=similar(a)
    for j in eachindex(x)
        step=h*max(1.0,abs(x[j]));xp=copy(x);xm=copy(x);xp[j]+=step;xm[j]-=step
        f(a,xp);f(b,xm);J[:,j]=(a-b)/(2step)
    end
    J
end
function equilibrium(seed,s;tol=1e-9)
    x=copy(seed);f=(du,u)->rhs!(du,u,s,0.0);du=similar(x)
    for it in 1:60
        f(du,x);err=maximum(abs.(du));err<tol && return x,err
        step=jacobian(f,x)\du;ok=false
        for k in 0:16
            q=x-step*2.0^(-k);ff=similar(x);f(ff,q)
            if maximum(abs.(ff))<err;x=q;ok=true;break;end
        end
        ok || break
    end
    f(du,x);x,maximum(abs.(du))
end
spectrum(x,s;h=1e-6)=eigvals(jacobian((du,u)->rhs!(du,u,s,0.0),x;h))
end
