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
