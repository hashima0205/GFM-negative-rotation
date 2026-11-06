include(joinpath(@__DIR__,"../src/study.jl"))
if abspath(PROGRAM_FILE)==@__FILE__
 rows=filter(r->r["case"] in STUDY["cases"]["main"],readcases(joinpath(ROOT,"inputs/cases.csv")))
 arg=findfirst(==("--output"),ARGS);output=arg===nothing ? joinpath(ROOT,"outputs","local_basins") : abspath(ARGS[arg+1])
 contexts=[findroots(r;output) for r in rows]
 if !("--roots-only" in ARGS)
  jobs=[]
  for ctx in contexts
   mkpath(joinpath(ctx.dir,"points"))
   local_settings=TOML.parsefile(joinpath(ROOT,"inputs/local_basin.toml"))
   angles=range(ctx.theta+local_settings["angle_offset_rad"][1],ctx.theta+local_settings["angle_offset_rad"][2];length=local_settings["angle_count"])
   freqs=local_settings["frequency_Hz"]
   open(joinpath(ctx.dir,"section.toml"),"w") do io
    TOML.print(io,Dict("angle_axis"=>collect(angles),"frequency_axis"=>collect(freqs),"angle_reference"=>"fixed slack Bus6; arithmetic mean internal angles of buses 2,3,7", "frequency_reference"=>"60 Hz; arithmetic mean internal frequency deviations of buses 2,3,7","washout_initial"=>"zero for all four machines; independent of imposed frequency","horizon_s"=>local_settings["horizon_s"],"save_s"=>local_settings["save_s"],"rotation_of_electrical_states"=>"Vc, If and Ig of buses 2,3,7 rotate by the imposed common angle shift; dq PI integrators, Qf and Bus1 remain at the postfault stable equilibrium"))
   end
   for (id,(df,theta)) in enumerate(Iterators.product(freqs,angles));push!(jobs,(ctx,id,theta,df));end
  end
  Threads.@threads :dynamic for i in eachindex(jobs)
   ctx,id,theta,df=jobs[i];basinpoint(ctx,id,theta,df)
  end
 end
end
