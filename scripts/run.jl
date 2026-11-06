include(joinpath(@__DIR__,"../src/model.jl"))
using .GFMModel, OrdinaryDiffEq, DelimitedFiles, LinearAlgebra, TOML, SHA
const ROOT=normpath(joinpath(@__DIR__,".."))
function readcases(file)
 lines=readlines(file);headers=split(lines[1],',')
 [Dict(String(k)=>String(v) for (k,v) in zip(headers,split(l,','))) for l in lines[2:end] if !isempty(strip(l))]
end
function solvepart(y,s,a,b;strict=false,step=.02)
 ts=sort(unique(vcat(collect(a:step:b),[a,b])))
 solve(ODEProblem(rhs!,copy(y),(a,b),s),Rodas5P();reltol=strict ? 1e-10 : 1e-9,
       abstol=strict ? 1e-12 : 1e-11,dtmax=strict ? .0025 : .005,
       saveat=ts,save_everystep=false,dense=false,maxiters=10^8)
end
function classify(t,u,s,target)
 c=s.config;tail=findall(t.>=t[end]-min(50.,t[end]/3));out=[]
 interp(v,q)=begin i=clamp(searchsortedlast(t,q),1,length(t)-1);v[i]+(v[i+1]-v[i])*(q-t[i])/(t[i+1]-t[i]) end
 for (j,b) in enumerate(BUS)
  k=13(j-1);angle=[x[k+13] for x in u]
  df=c.control=="VSM" ? [60x[k+12] for x in u] : [60c.mp*(c.machines[j].Pset-x[k+12]) for x in u]
  shift=angle.-angle[1];turns=shift[end]/(2pi);err=abs(atan(sin(angle[end]-target[k+13]),cos(angle[end]-target[k+13])))
  width=maximum(angle[tail])-minimum(angle[tail]);fmax=maximum(abs.(df[tail]))
  windows=diff([interp(angle,q) for q in range(.4t[end],t[end];length=4)])/(2pi)
  label=if fmax<1e-4 && err<.002 && width<.005
   maximum(abs.(shift))>=2pi ? "recovery_after_slip" : "recovery"
  elseif turns< -2 && maximum(windows)< -.2 && sum(windows)/(.6t[end])< -1e-4
   "negative_running"
  elseif turns>2 && minimum(windows)>.2 && sum(windows)/(.6t[end])>1e-4
   "positive_running"
  else;"unresolved";end
  push!(out,(b,label,turns,sum(df[tail])/length(tail),fmax,err,width,minimum(windows),maximum(windows)))
 end
 out
end
function writecsv(path,header,rows)
 open(path,"w") do io
  println(io,join(header,','));for row in rows;println(io,join(row,','));end
 end
end
function compress(path)
 run(`gzip -f $path`)
end
function run_case(row;strict=false,horizon=nothing,save=true)
 c=load_config(joinpath(ROOT,"inputs",row["config"]),row)
 tag=row["case"]*(strict ? "_strict" : "");dir=joinpath(ROOT,"results",tag);mkpath(dir)
 h=horizon===nothing ? parse(Float64,row["horizon"]) : horizon
 seedfile=startswith(tag,"original") ? joinpath(ROOT,"provenance/reference_results","droop_original_"*(occursin("_A",tag) ? "A" : "B")*"_pre_initial.csv") : joinpath(ROOT,"inputs/pre_seed_legacy.csv")
 seed=vec(readdlm(seedfile,',',Float64));pre_s=make_stage(c,"pre");post_s=make_stage(c,"post")
 y0,ep=equilibrium(legacy_to_native(seed,c),pre_s)
 target_seed=vec(readdlm(joinpath(ROOT,"inputs",startswith(tag,"original") ? "original_post_seed_legacy.csv" : "post_seed_legacy.csv"),',',Float64))
 target,eq=equilibrium(legacy_to_native(target_seed,c),post_s)
 @assert max(ep,eq)<1e-8
 evpre=spectrum(y0,pre_s);evpost=spectrum(target,post_s)
 @assert maximum(real.(evpre))<0 && maximum(real.(evpost))<0
 if row["config"]=="common.toml";@assert c.B>0 && abs(voltages(y0,pre_s)[5])>=.98;end
 writecsv(joinpath(dir,"equilibria.csv"),["stage","residual","max_real_eigen","unstable_modes"],[("pre",ep,maximum(real.(evpre)),sum(real.(evpre).>1e-7)),("post",eq,maximum(real.(evpost)),sum(real.(evpost).>1e-7))])
 writedlm(joinpath(dir,"pre_root.csv"),y0,',');writedlm(joinpath(dir,"post_root.csv"),target,',')
 writedlm(joinpath(dir,"post_root_legacy.csv"),native_to_legacy(target,post_s),',')
 println("CASE_START ",tag," horizon=",h," preeig=",maximum(real.(evpre))," posteig=",maximum(real.(evpost)));flush(stdout)
 schedules=[("pre",0.,c.fault_on,.01),("fault",c.fault_on,c.clearing,.0005),("post",c.clearing,c.clearing+h,.02)]
 parts=[];y=copy(y0);events=[];tick=time()
 for (name,a,b,step) in schedules
  s=make_stage(c,name);initial=copy(y);sol=solvepart(y,s,a,b;strict,step)
  @assert string(sol.retcode)=="Success";push!(parts,(;name,s,sol))
  push!(events,(name,maximum(abs.(initial-sol.u[1])),c.control=="VSM" ? maximum(abs.(initial[53:56]-sol.u[1][53:56])) : 0.0,sol.destats.naccept,sol.destats.nreject))
  y=copy(sol.u[end]);println("STAGE_DONE ",tag," ",name," wall_s=",time()-tick);flush(stdout)
 end
 post=parts[end];machines=classify(post.sol.t.-c.clearing,post.sol.u,post_s,target)
 writecsv(joinpath(dir,"machines.csv"),["bus","classification","turns","tail_mean_df_Hz","tail_max_abs_df_Hz","phase_error_rad","phase_width_rad","min_window_turns","max_window_turns"],machines)
 writecsv(joinpath(dir,"events.csv"),["stage","differential_jump","washout_jump","accepted_internal_steps","rejected_internal_steps"],events)
 if save
  sf=joinpath(dir,"states.csv");of=joinpath(dir,"observations.csv")
  open(sf,"w") do io
   println(io,join(vcat(["t_absolute_s","t_post_s","stage"],["x$i" for i in eachindex(y0)]),','))
   for part in parts,(t,x) in zip(part.sol.t,part.sol.u);println(io,join(vcat(Any[t,t-c.clearing,part.name],x),','));end
  end
  names=["delta_rad","df_Hz","omega_rad_s","Vc_pu","Ig_pu","If_pu","U_pu","Pcap_pu","Qcap_pu","Pterminal_pu","Qterminal_pu","ref_in_d_pu","ref_in_q_pu","ref_out_d_pu","ref_out_q_pu","limit_factor","saturated","Qf_pu","Pfilter_pu","nu_pu","washout_z","U_r_pu","U_i_pu","Ig_r_pu","Ig_i_pu"]
  maxalg=0.
  open(of,"w") do io
   println(io,join(vcat(["t_absolute_s","t_post_s","stage"],["b$(b)_$(n)" for b in BUS for n in names],"algebraic_residual"),','))
   for part in parts,(t,x) in zip(part.sol.t,part.sol.u)
    u=voltages(x,part.s);inj=zeros(ComplexF64,8);v=Any[t,t-c.clearing,part.name]
    for (j,a) in enumerate(measurements(x,part.s))
     k=13(j-1);inj[BUS[j]]=a.ig
     append!(v,[a.δ,60a.nu,c.machines[j].w0*(1+a.nu),abs(a.vc),abs(a.ig),abs(a.iff),abs(a.u),a.pcap,a.qcap,real(a.terminal),imag(a.terminal),a.ud,a.uq,a.rd,a.rq,a.factor,Int(a.factor<1),x[k+11],c.control=="Droop" ? x[k+12] : NaN,a.nu,c.control=="VSM" ? x[52+j] : NaN,real(a.u),imag(a.u),real(a.ig),imag(a.ig)])
    end
    residual=maximum(abs.((part.s.Y*u-inj)[GFMModel.NONSLACK]));maxalg=max(maxalg,residual)
    println(io,join(vcat(v,residual),','))
   end
  end
  compress(sf);compress(of)
  writecsv(joinpath(dir,"validation.csv"),["max_algebraic_residual","max_differential_jump","max_washout_jump","reltol","abstol","dtmax_s","regular_post_save_s","horizon_s","runtime_s"],[(maxalg,maximum(e[2] for e in events),maximum(e[3] for e in events),strict ? 1e-10 : 1e-9,strict ? 1e-12 : 1e-11,strict ? .0025 : .005,.02,h,time()-tick)])
 end
 open(joinpath(dir,"settings.toml"),"w") do io;TOML.print(io,Dict("case"=>row,"strict"=>strict,"actual_horizon_s"=>h));end
 println("CASE_DONE ",tag," ",join([m[2] for m in machines],',')," remote_turns=",sum(m[3] for m in machines[2:4])/3," wall_s=",time()-tick);flush(stdout)
 (;row,c,dir,parts,target,machines)
end
if abspath(PROGRAM_FILE)==@__FILE__
 file=joinpath(ROOT,"inputs",isempty(ARGS) ? "cases.csv" : ARGS[1]);selection=length(ARGS)>1 ? split(ARGS[2],',') : nothing
 strict="--strict" in ARGS;harg=findfirst(==("--horizon"),ARGS);horizon=harg===nothing ? nothing : parse(Float64,ARGS[harg+1])
 for row in readcases(file);selection!==nothing && !(row["case"] in selection) && continue;run_case(row;strict,horizon);end
end
