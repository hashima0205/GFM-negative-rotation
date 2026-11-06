include(joinpath(@__DIR__,"run.jl"))
using Base.Threads
function section(target,s,theta,df)
 y=copy(target);meanangle=sum(y[[26,39,52]])/3;shift=theta-meanangle;rot=cis(shift)
 for j in 2:4
  k=13(j-1);y[k+13]+=shift
  for (r,i) in [(4,3),(6,5),(8,7)]
   a=complex(y[k+r],y[k+i])*rot;y[k+r]=real(a);y[k+i]=imag(a)
  end
  y[k+12]=s.config.control=="VSM" ? df/60 : s.config.machines[j].Pset-df/(60s.config.mp)
 end
 s.config.control=="VSM" && (y[53:56].=0.0)
 y
end
function coordinates(y,s)
 meanangle=sum(y[[26,39,52]])/3
 freq=s.config.control=="VSM" ? sum(y[[25,38,51]])*20 : sum(60s.config.mp*(s.config.machines[j].Pset-y[13(j-1)+12]) for j in 2:4)/3
 meanangle,freq
end
function signature_for_case(row)
 files=[joinpath(ROOT,p) for p in ["src/model.jl","scripts/run.jl","scripts/basins.jl","Project.toml","Manifest.toml"]]
 append!(files,[joinpath(ROOT,"inputs",row["config"]),joinpath(ROOT,"results",row["case"],"post_root.csv")])
 rowtext=join([k*"="*row[k] for k in sort(collect(keys(row)))],"\n")
 bytes2hex(sha256(rowtext*join(bytes2hex(sha256(read(p))) for p in files)))
end
function check_signature(row,dir)
 path=joinpath(dir,"configuration.sha256");expected=signature_for_case(row)
 if isfile(path)
  @assert strip(read(path,String))==expected "Basin inputs/model/environment changed: use a new output directory; old labels must not be reused."
 else
  points=joinpath(dir,"points")
  @assert !isdir(points) || isempty(readdir(points)) "Existing basin points lack a configuration signature; do not reuse them."
  write(path,expected*"\n")
 end
end
function findroots(row)
 c=load_config(joinpath(ROOT,"inputs",row["config"]),row);s=make_stage(c,"post")
 target=vec(readdlm(joinpath(ROOT,"results",row["case"],"post_root.csv"),',',Float64));theta=sum(target[[26,39,52]])/3
 dir=joinpath(ROOT,"results/basins",row["case"]);mkpath(dir)
 check_signature(row,dir)
 roots=[target];records=[]
 for shift in [-2.5,-1.5,-.7,-.3,-.1,.1,.3,.7,1.5,2.5]
  seed=section(target,s,theta+shift,0.);x,er=equilibrium(seed,s)
  er<1e-8 || continue
  if all(maximum(abs.(x-r))>1e-4 for r in roots)
   push!(roots,x)
  end
 end
 for (i,x) in enumerate(roots)
  ev=spectrum(x,s);n=sum(real.(ev).>1e-7);res=zeros(length(x));rhs!(res,x,s,0.)
  name=n==0 ? "stable" : n==1 ? "saddle" : "unstable_$(n)"
  writedlm(joinpath(dir,"root_$(i)_$(name).csv"),x,',')
  push!(records,(i,name,coordinates(x,s)...,maximum(abs.(res)),maximum(real.(ev)),n))
 end
 writecsv(joinpath(dir,"roots.csv"),["root_id","kind","remote_angle_rad","remote_df_Hz","residual","max_real_eigen","unstable_modes"],records)
 println("ROOTS ",row["case"]," ",records);flush(stdout)
 (;row,c,s,target,dir,theta)
end
function basinpoint(context,id,theta,df;horizon=1000.)
 (;row,c,s,target,dir)=context
 path=joinpath(dir,"points",lpad(id,3,'0')*".toml");isfile(path)&&return
 y=section(target,s,theta,df);actual,freq=coordinates(y,s);u0=voltages(y,s)
 inj=zeros(ComplexF64,8)
 for j in 1:4;inj[BUS[j]]=complex(y[13(j-1)+4],y[13(j-1)+3]);end
 alg=maximum(abs.((s.Y*u0-inj)[GFMModel.NONSLACK]))
 @assert abs(actual-theta)<1e-10 && abs(freq-df)<1e-10 && alg<1e-10
 tick=time();sol=solvepart(y,s,0.,horizon;step=.2)
 success=string(sol.retcode)=="Success"
 machines=classify(sol.t,sol.u,s,target)
 labels=[m[2] for m in machines]
 label=!success ? "numerical_failure" : all(l in ["recovery","recovery_after_slip"] for l in labels) ? "recovery" : "negative_running" in labels ? "negative_running" : "positive_running" in labels ? "positive_running" : "unresolved"
 result=Dict("point"=>id,"theta_requested"=>theta,"df_requested"=>df,"theta_actual"=>actual,"df_actual"=>freq,"initial_algebraic_residual"=>alg,"classification"=>label,"machine_labels"=>labels,"retcode"=>string(sol.retcode),"horizon_s"=>sol.t[end],"runtime_s"=>time()-tick,"initial_native"=>y,"initial_bus_voltage_ri"=>[[real(v),imag(v)] for v in u0],"final_native"=>sol.u[end],"final_bus_voltage_ri"=>[[real(v),imag(v)] for v in voltages(sol.u[end],s)],"machine_metrics"=>[collect(string.(m)) for m in machines])
 open(path,"w") do io;TOML.print(io,result);end
 # Keep one full representative per row and the stable-column points, with no averaging of machines.
 if id%7==4 || id in [1,7,26,43,49]
  trajectory=joinpath(dir,"points",lpad(id,3,'0')*"_trajectory.csv")
  writecsv(trajectory,vcat(["t_s"],["x$i" for i in eachindex(y)]),[vcat(t,x) for (t,x) in zip(sol.t,sol.u)])
  compress(trajectory)
 end
 println("BASIN_DONE ",row["case"]," ",id," ",label," ",round(time()-tick;digits=2),"s");flush(stdout)
end
if abspath(PROGRAM_FILE)==@__FILE__
 rows=filter(r->r["case"] in ["A","B","C"],readcases(joinpath(ROOT,"inputs/cases.csv")))
 contexts=[findroots(r) for r in rows]
 if !("--roots-only" in ARGS)
  jobs=[]
  for ctx in contexts
   mkpath(joinpath(ctx.dir,"points"))
   angles=range(ctx.theta-.08,ctx.theta+.08;length=7)
   freqs=[-.04,-.015,-.005,0.,.005,.015,.04]
   open(joinpath(ctx.dir,"section.toml"),"w") do io
    TOML.print(io,Dict("angle_axis"=>collect(angles),"frequency_axis"=>collect(freqs),"angle_reference"=>"fixed slack Bus6; arithmetic mean internal angles of buses 2,3,7", "frequency_reference"=>"60 Hz; arithmetic mean internal frequency deviations of buses 2,3,7","washout_initial"=>"zero for all four machines; independent of imposed frequency","horizon_s"=>1000.0,"save_s"=>.2,"rotation_of_electrical_states"=>"Vc, If and Ig of buses 2,3,7 rotate by the imposed common angle shift; dq PI integrators, Qf and Bus1 remain at the postfault stable equilibrium"))
   end
   for (id,(df,theta)) in enumerate(Iterators.product(freqs,angles));push!(jobs,(ctx,id,theta,df));end
  end
  Threads.@threads :dynamic for i in eachindex(jobs)
   ctx,id,theta,df=jobs[i];basinpoint(ctx,id,theta,df)
  end
 end
end
