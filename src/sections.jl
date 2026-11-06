function findroots(row;output=joinpath(ROOT,"outputs/local_basins"))
 c=load_config(joinpath(ROOT,"inputs",row["config"]),row);s=make_stage(c,"post")
 verify_reference(joinpath(result_root(),row["case"]) )
 target=vec(readdlm(joinpath(result_root(),row["case"],"post_root.csv"),',',Float64));theta=sum(target[[26,39,52]])/3
 dir=joinpath(output,row["case"]);mkpath(dir)
 prepare_output(dir,row;kind="local_section",section="inputs/local_basin.toml",resume=true)
 roots=[target];records=[]
 for shift in TOML.parsefile(joinpath(ROOT,"inputs/local_basin.toml"))["root_seed_shifts_rad"]
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
function basinpoint(context,id,theta,df;horizon=TOML.parsefile(joinpath(ROOT,"inputs/local_basin.toml"))["horizon_s"])
 (;row,c,s,target,dir)=context
 path=joinpath(dir,"points",lpad(id,3,'0')*".toml");isfile(path)&&return
 y=section(target,s,theta,df);actual,freq=coordinates(y,s);u0=voltages(y,s)
 inj=zeros(ComplexF64,8)
 for j in 1:4;inj[BUS[j]]=complex(y[13(j-1)+4],y[13(j-1)+3]);end
 alg=maximum(abs.((s.Y*u0-inj)[GFMModel.NONSLACK]))
 @assert abs(actual-theta)<1e-10 && abs(freq-df)<1e-10 && alg<1e-10
 tick=time();sol=solvepart(y,s,0.,horizon;step=TOML.parsefile(joinpath(ROOT,"inputs/local_basin.toml"))["save_s"])
 success=string(sol.retcode)=="Success"
 machines=classify(sol.t,sol.u,s,target)
 labels=[m[2] for m in machines]
 label=aggregate_label(labels,success)
 result=Dict("point"=>id,"theta_requested"=>theta,"df_requested"=>df,"theta_actual"=>actual,"df_actual"=>freq,"initial_algebraic_residual"=>alg,"classification"=>label,"machine_labels"=>labels,"retcode"=>string(sol.retcode),"horizon_s"=>sol.t[end],"runtime_s"=>time()-tick,"initial_native"=>y,"initial_bus_voltage_ri"=>[[real(v),imag(v)] for v in u0],"final_native"=>sol.u[end],"final_bus_voltage_ri"=>[[real(v),imag(v)] for v in voltages(sol.u[end],s)],"machine_metrics"=>[collect(string.(m)) for m in machines])
 open(path,"w") do io;TOML.print(io,result);end
 # Keep one full representative per row and the stable-column points, with no averaging of machines.
 settings=TOML.parsefile(joinpath(ROOT,"inputs/local_basin.toml"))
 if id%settings["representative_modulus"]==settings["representative_remainder"] || id in settings["representative_ids"]
  trajectory=joinpath(dir,"points",lpad(id,3,'0')*"_trajectory.csv")
  writecsv(trajectory,vcat(["t_s"],["x$i" for i in eachindex(y)]),[vcat(t,x) for (t,x) in zip(sol.t,sol.u)])
  compress(trajectory)
 end
 println("BASIN_DONE ",row["case"]," ",id," ",label," ",round(time()-tick;digits=2),"s");flush(stdout)
end
function frozen_context(row;output=joinpath(ROOT,"outputs/fault_basins"))
    c=load_config(joinpath(ROOT,"inputs",row["config"]),row);s=make_stage(c,"post")
    verify_reference(joinpath(result_root(),row["case"]) )
    target=vec(readdlm(joinpath(result_root(),row["case"],"post_root.csv"),',',Float64))
    dir=joinpath(output,row["case"])
    prepare_output(dir,row;kind="frozen_section",section="inputs/fault_basin.toml",resume=true)
    mkpath(joinpath(dir,"points"))
    (;row,c,s,target,dir)
end
function frozen_point(ctx,id,theta,df,grid,settings)
    (;row,c,s,target,dir)=ctx
    path=joinpath(dir,"points",lpad(id,3,'0')*".toml");isfile(path)&&return
    y=frozen_section(target,s,theta,df);actual,freq=phase_coordinates(y,s);u0=voltages(y,s)
    changed=vcat(stateindices(:angle;remote=true),stateindices(:frequency;remote=true));fixed=setdiff(eachindex(y),changed)
    frozen_error=maximum(abs.(y[fixed]-target[fixed]))
    inj=zeros(ComplexF64,8)
    for j in 1:4;inj[BUS[j]]=complex(y[13(j-1)+4],y[13(j-1)+3]);end
    alg=maximum(abs.((s.Y*u0-inj)[GFMModel.NONSLACK]))
    @assert abs(actual-theta)<1e-10 && abs(freq-df)<1e-10 && alg<1e-10 && frozen_error==0
    tick=time();sol=solvepart(y,s,0.,settings["horizon_s"];step=settings["save_s"])
    success=string(sol.retcode)=="Success";machines=classify(sol.t,sol.u,s,target);labels=[m[2] for m in machines]
    label=aggregate_label(labels,success)
    result=Dict("point"=>id,"grid"=>grid,"theta_requested"=>theta,"df_requested"=>df,"theta_actual"=>actual,"df_actual"=>freq,"initial_algebraic_residual"=>alg,"max_frozen_state_error"=>frozen_error,"classification"=>label,"machine_labels"=>labels,"retcode"=>string(sol.retcode),"horizon_s"=>sol.t[end],"runtime_s"=>time()-tick,"initial_native"=>y,"initial_bus_voltage_ri"=>[[real(v),imag(v)] for v in u0],"final_native"=>sol.u[end],"final_bus_voltage_ri"=>[[real(v),imag(v)] for v in voltages(sol.u[end],s)],"machine_metrics"=>[collect(string.(m)) for m in machines])
    # Retain the projected trajectory of every point; no temporal averaging or smoothing.
    projection=joinpath(dir,"points",lpad(id,3,'0')*"_projection.csv")
    header=vcat(["t_s","theta_rad","df_Hz"],["b$(b)_delta_rad" for b in BUS],["b$(b)_df_Hz" for b in BUS])
    writecsv(projection,header,[vcat(t,collect(phase_coordinates(x,s)),[x[13(j-1)+13] for j in 1:4],[c.control=="VSM" ? frequency_base(c)*x[13(j-1)+12] : frequency_base(c)*c.mp*(c.machines[j].Pset-x[13(j-1)+12]) for j in 1:4]) for (t,x) in zip(sol.t,sol.u)])
    compress(projection)
    open(path,"w") do io;TOML.print(io,result);end
    println("FROZEN_BASIN_DONE ",row["case"]," ",id," ",label," ",round(time()-tick;digits=2),"s");flush(stdout)
end
