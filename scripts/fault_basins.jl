include(joinpath(@__DIR__,"../src/study.jl"))
if abspath(PROGRAM_FILE)==@__FILE__
    settings=TOML.parsefile(SECTION_INPUT)
    points=vcat([(a,f,"global") for f in settings["frequency_Hz"] for a in settings["angle_rad"]],[(a,f,"local") for f in settings["local_frequency_Hz"] for a in settings["local_angle_rad"]])
    rows=filter(r->r["case"] in STUDY["cases"]["main"],readcases(joinpath(ROOT,"inputs/cases.csv")))
 arg=findfirst(==("--output"),ARGS);output=arg===nothing ? joinpath(ROOT,"outputs","fault_basins") : abspath(ARGS[arg+1])
    contexts=[frozen_context(r;output) for r in rows];jobs=[]
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
