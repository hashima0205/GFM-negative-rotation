# Post-fault conditional sections, with the historical frozen-electrical-state prescription.
# The real pre/fault/post trajectories are read separately by the plotting script.
include(joinpath(@__DIR__,"run.jl"))
using Base.Threads
const SECTION_INPUT=joinpath(ROOT,"inputs/fault_basin.toml")
function phase_coordinates(y,s)
    theta=sum(y[[26,39,52]])/3
    df=s.config.control=="VSM" ? 60sum(y[[25,38,51]])/3 : sum(60s.config.mp*(s.config.machines[j].Pset-y[13(j-1)+12]) for j in 2:4)/3
    theta,df
end
function frozen_section(target,s,theta,df)
    y=copy(target);shift=theta-sum(target[[26,39,52]])/3
    for j in 2:4
        k=13(j-1);y[k+13]+=shift
        y[k+12]=s.config.control=="VSM" ? df/60 : s.config.machines[j].Pset-df/(60s.config.mp)
    end
    # All Vc/If/Ig, dq PI integrators, Qf, Bus1 and washout states remain at the root.
    y
end
function fault_basin_signature(row)
    files=[joinpath(ROOT,p) for p in ["src/model.jl","scripts/run.jl","scripts/fault_basins.jl","Project.toml","Manifest.toml","inputs/fault_basin.toml"]]
    append!(files,[joinpath(ROOT,"inputs",row["config"]),joinpath(ROOT,"results",row["case"],"post_root.csv")])
    rowtext=join([k*"="*row[k] for k in sort(collect(keys(row)))],"\n")
    bytes2hex(sha256(rowtext*join(bytes2hex(sha256(read(p))) for p in files)))
end
function frozen_context(row)
    c=load_config(joinpath(ROOT,"inputs",row["config"]),row);s=make_stage(c,"post")
    target=vec(readdlm(joinpath(ROOT,"results",row["case"],"post_root.csv"),',',Float64))
    dir=joinpath(ROOT,"results/fault_basins",row["case"]);mkpath(joinpath(dir,"points"))
    sig=fault_basin_signature(row);sigfile=joinpath(dir,"configuration.sha256")
    if isfile(sigfile)
        @assert strip(read(sigfile,String))==sig "Changed section/model/inputs: use a new output directory."
    else
        @assert isempty(readdir(joinpath(dir,"points")))
        write(sigfile,sig*"\n")
    end
    (;row,c,s,target,dir)
end
function frozen_point(ctx,id,theta,df,grid,settings)
    (;row,c,s,target,dir)=ctx
    path=joinpath(dir,"points",lpad(id,3,'0')*".toml");isfile(path)&&return
    y=frozen_section(target,s,theta,df);actual,freq=phase_coordinates(y,s);u0=voltages(y,s)
    changed=[25,26,38,39,51,52];fixed=setdiff(eachindex(y),changed)
    frozen_error=maximum(abs.(y[fixed]-target[fixed]))
    inj=zeros(ComplexF64,8)
    for j in 1:4;inj[BUS[j]]=complex(y[13(j-1)+4],y[13(j-1)+3]);end
    alg=maximum(abs.((s.Y*u0-inj)[GFMModel.NONSLACK]))
    @assert abs(actual-theta)<1e-10 && abs(freq-df)<1e-10 && alg<1e-10 && frozen_error==0
    tick=time();sol=solvepart(y,s,0.,settings["horizon_s"];step=settings["save_s"])
    success=string(sol.retcode)=="Success";machines=classify(sol.t,sol.u,s,target);labels=[m[2] for m in machines]
    label=!success ? "numerical_failure" : all(l in ["recovery","recovery_after_slip"] for l in labels) ? "recovery" : "negative_running" in labels ? "negative_running" : "positive_running" in labels ? "positive_running" : "unresolved"
    result=Dict("point"=>id,"grid"=>grid,"theta_requested"=>theta,"df_requested"=>df,"theta_actual"=>actual,"df_actual"=>freq,"initial_algebraic_residual"=>alg,"max_frozen_state_error"=>frozen_error,"classification"=>label,"machine_labels"=>labels,"retcode"=>string(sol.retcode),"horizon_s"=>sol.t[end],"runtime_s"=>time()-tick,"initial_native"=>y,"initial_bus_voltage_ri"=>[[real(v),imag(v)] for v in u0],"final_native"=>sol.u[end],"final_bus_voltage_ri"=>[[real(v),imag(v)] for v in voltages(sol.u[end],s)],"machine_metrics"=>[collect(string.(m)) for m in machines])
    # Retain the projected trajectory of every point; no temporal averaging or smoothing.
    projection=joinpath(dir,"points",lpad(id,3,'0')*"_projection.csv")
    header=vcat(["t_s","theta_rad","df_Hz"],["b$(b)_delta_rad" for b in BUS],["b$(b)_df_Hz" for b in BUS])
    writecsv(projection,header,[vcat(t,collect(phase_coordinates(x,s)),[x[13(j-1)+13] for j in 1:4],[c.control=="VSM" ? 60x[13(j-1)+12] : 60c.mp*(c.machines[j].Pset-x[13(j-1)+12]) for j in 1:4]) for (t,x) in zip(sol.t,sol.u)])
    compress(projection)
    open(path,"w") do io;TOML.print(io,result);end
    println("FROZEN_BASIN_DONE ",row["case"]," ",id," ",label," ",round(time()-tick;digits=2),"s");flush(stdout)
end
if abspath(PROGRAM_FILE)==@__FILE__
    settings=TOML.parsefile(SECTION_INPUT)
    points=vcat([(a,f,"global") for f in settings["frequency_Hz"] for a in settings["angle_rad"]],[(a,f,"local") for f in settings["local_frequency_Hz"] for a in settings["local_angle_rad"]])
    rows=filter(r->r["case"] in ["A","B","C"],readcases(joinpath(ROOT,"inputs/cases.csv")))
    contexts=[frozen_context(r) for r in rows];jobs=[]
    for ctx in contexts
        open(joinpath(ctx.dir,"section.toml"),"w") do io
            TOML.print(io,Dict("input"=>"inputs/fault_basin.toml","point_count"=>length(points),"angle_reference"=>"fixed slack Bus6; arithmetic mean unwrapped internal angles of buses 2,3,7","frequency_reference"=>"60 Hz; arithmetic mean internal frequency deviations of buses 2,3,7","changed_states"=>"Only remote internal angles and frequency/P-filter coordinates; remote angle offsets are retained.","frozen_initial_states"=>"All other differential states, including unrotated Vc/If/Ig, all dq PI integrators, Qf, Bus1 and all VSM washout z, remain at the post-fault stable equilibrium. All states evolve after initialization.","algebraic_variables"=>"Reconstructed exactly with the post-fault network; never frozen independently.","physical_fault_trajectory"=>"Separate projection of saved pre/fault/post observations; generally outside this initial-state section.","horizon_s"=>settings["horizon_s"],"save_s"=>settings["save_s"]))
        end
        for (id,(a,f,g)) in enumerate(points);push!(jobs,(ctx,id,a,f,g));end
    end
    Threads.@threads :dynamic for i in eachindex(jobs)
        ctx,id,a,f,g=jobs[i];frozen_point(ctx,id,a,f,g,settings)
    end
    println("FROZEN_BASINS_COMPLETE");flush(stdout)
end
