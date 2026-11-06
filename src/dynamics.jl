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
    factor=min(one(ud),m.Imax/sqrt(ud^2+uq^2+STUDY["network"]["command_norm_regularizer"]))
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
