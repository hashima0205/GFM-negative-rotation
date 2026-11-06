function classify(t,u,s,target)
 c=s.config;rules=STUDY["classification"];tail=findall(t.>=t[end]-min(rules["tail_max_s"],t[end]/rules["tail_divisor"]));out=[]
 interp(v,q)=begin i=clamp(searchsortedlast(t,q),1,length(t)-1);v[i]+(v[i+1]-v[i])*(q-t[i])/(t[i+1]-t[i]) end
 for (j,b) in enumerate(BUS)
  k=13(j-1);angle=[x[k+13] for x in u]
  df=c.control=="VSM" ? [frequency_base(c)*x[k+12] for x in u] : [frequency_base(c)*c.mp*(c.machines[j].Pset-x[k+12]) for x in u]
  shift=angle.-angle[1];turns=shift[end]/(2pi);err=abs(atan(sin(angle[end]-target[k+13]),cos(angle[end]-target[k+13])))
  width=maximum(angle[tail])-minimum(angle[tail]);fmax=maximum(abs.(df[tail]))
  windows=diff([interp(angle,q) for q in range(rules["running_tail_start"]*t[end],t[end];length=rules["running_windows"]+1)])/(2pi)
  label=if fmax<rules["recovery_df_Hz"] && err<rules["recovery_phase_rad"] && width<rules["recovery_width_rad"]
   maximum(abs.(shift))>=2pi ? "recovery_after_slip" : "recovery"
  elseif turns< -rules["running_min_turns"] && maximum(windows)< -rules["running_window_turns"] && sum(windows)/((1-rules["running_tail_start"])*t[end])< -rules["running_rate_turns_per_s"]
   "negative_running"
  elseif turns>rules["running_min_turns"] && minimum(windows)>rules["running_window_turns"] && sum(windows)/((1-rules["running_tail_start"])*t[end])>rules["running_rate_turns_per_s"]
   "positive_running"
  else;"unresolved";end
  push!(out,(b,label,turns,sum(df[tail])/length(tail),fmax,err,width,minimum(windows),maximum(windows)))
 end
 out
end

function coordinates(y,s)
    theta=sum(y[stateindices(:angle;remote=true)])/length(REMOTE)
    freq=sum(internal_frequency(y,s.config,j) for (j,b) in enumerate(BUS) if b in REMOTE)/length(REMOTE)
    theta,freq
end
phase_coordinates(y,s)=coordinates(y,s)
function initial_section(target,s,theta,df;rotate_electrical=false)
    y=copy(target);shift=theta-coordinates(target,s)[1];rot=cis(shift)
    for (j,b) in enumerate(BUS)
        b in REMOTE || continue
        k=13(j-1);y[k+13]+=shift
        if rotate_electrical
            for (r,i) in [(4,3),(6,5),(8,7)]
                a=complex(y[k+r],y[k+i])*rot;y[k+r]=real(a);y[k+i]=imag(a)
            end
        end
        y[k+12]=s.config.control=="VSM" ? df/frequency_base(s.config) : s.config.machines[j].Pset-df/(frequency_base(s.config)*s.config.mp)
    end
    rotate_electrical && s.config.control=="VSM" && (y[53:56].=0.0)
    y
end
section(target,s,theta,df)=initial_section(target,s,theta,df;rotate_electrical=true)
frozen_section(target,s,theta,df)=initial_section(target,s,theta,df)
aggregate_label(labels,success=true)=!success ? "numerical_failure" : all(l in ["recovery","recovery_after_slip"] for l in labels) ? "recovery" : "negative_running" in labels ? "negative_running" : "positive_running" in labels ? "positive_running" : "unresolved"
