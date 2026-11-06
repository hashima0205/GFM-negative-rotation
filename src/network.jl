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
        active=(name=="post" && i in STUDY["network"]["opened_lines"]) ? 0.0 : 1.0
        y=active/complex(c.lines[i,1],c.lines[i,2])
        Y[a,a]+=y;Y[b,b]+=y;Y[a,b]-=y;Y[b,a]-=y
    end
    Y[STUDY["network"]["load_bus"],STUDY["network"]["load_bus"]]+=complex(c.G,c.B)
    name=="fault" && (Y[STUDY["network"]["fault_bus"],STUDY["network"]["fault_bus"]]+=c.faultG)
    E=zeros(ComplexF64,7,4)
    for (j,b) in enumerate(BUS); E[findfirst(==(b),NONSLACK),j]=1;end
    W=zeros(ComplexF64,8,4);v0=zeros(ComplexF64,8);v0[SLACK]=1
    W[NONSLACK,:]=Y[NONSLACK,NONSLACK]\E
    v0[NONSLACK]=-Y[NONSLACK,NONSLACK]\Y[NONSLACK,SLACK]
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
