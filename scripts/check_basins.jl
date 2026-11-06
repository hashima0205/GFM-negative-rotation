include(joinpath(@__DIR__,"basins.jl"))
function check_sections()
 records=[]
 for row in filter(r->r["case"] in ["A","B","C"],readcases(joinpath(ROOT,"inputs/cases.csv")))
  c=load_config(joinpath(ROOT,"inputs",row["config"]),row);s=make_stage(c,"post")
  dir=joinpath(ROOT,"results/basins",row["case"])
  target=vec(readdlm(joinpath(ROOT,"results",row["case"],"post_root.csv"),',',Float64))
  files=sort(filter(p->endswith(p,".toml"),readdir(joinpath(dir,"points");join=true)));@assert length(files)==49
  maxstate=0.;maxcoord=0.;maxvoltage=0.;maxalg=0.;labels=Dict{String,Int}()
  for file in files
   a=TOML.parsefile(file);y=Float64.(a["initial_native"]);yf=Float64.(a["final_native"])
   expected=section(target,s,a["theta_requested"],a["df_requested"])
   maxstate=max(maxstate,maximum(abs.(y-expected)))
   theta,freq=coordinates(y,s);maxcoord=max(maxcoord,abs(theta-a["theta_requested"]),abs(freq-a["df_requested"]))
   for (x,k) in [(y,"initial_bus_voltage_ri"),(yf,"final_bus_voltage_ri")]
    uu=voltages(x,s);stored=complex.([v[1] for v in a[k]],[v[2] for v in a[k]])
    maxvoltage=max(maxvoltage,maximum(abs.(uu-stored)))
    inj=zeros(ComplexF64,8)
    for j in 1:4;inj[BUS[j]]=complex(x[13(j-1)+4],x[13(j-1)+3]);end
    maxalg=max(maxalg,maximum(abs.((s.Y*uu-inj)[GFMModel.NONSLACK])))
   end
   @assert a["horizon_s"]==1000. && a["retcode"]=="Success"
   lab=a["classification"];labels[lab]=get(labels,lab,0)+1
  end
  @assert maxstate<1e-12 && maxcoord<1e-10 && maxvoltage<1e-12 && maxalg<1e-10
  roots=readdlm(joinpath(dir,"roots.csv"),',',Any;skipstart=1)
  saddle_mismatch=0.;maxroot=0.
  for rr in eachrow(roots)
   id=Int(rr[1]);kind=String(rr[2]);x=vec(readdlm(joinpath(dir,"root_$(id)_$(kind).csv"),',',Float64));f=zeros(length(x));rhs!(f,x,s,0.);maxroot=max(maxroot,maximum(abs.(f)))
   ev=spectrum(x,s;h=5e-7);n=sum(real.(ev).>1e-7)
   @assert kind=="stable" ? n==0 : kind=="saddle" ? n==1 : true
   if kind=="saddle"
    theta,freq=coordinates(x,s);saddle_mismatch=max(saddle_mismatch,maximum(abs.(section(target,s,theta,freq)-x)))
   end
  end
  @assert maxroot<1e-8
  push!(records,Dict("case"=>row["case"],"points"=>49,"max_initial_state_definition_error"=>maxstate,"max_coordinate_error"=>maxcoord,"max_reconstructed_voltage_error"=>maxvoltage,"max_algebraic_residual"=>maxalg,"max_root_residual"=>maxroot,"saddle_section_native_max_difference"=>saddle_mismatch,"classifications"=>labels))
 end
 mkpath(joinpath(ROOT,"results/validation"))
 open(joinpath(ROOT,"results/validation/basin_checks.toml"),"w") do io;TOML.print(io,Dict("cases"=>records));end
 println("BASIN_SECTION_CHECKS_OK ",records);records
end
if abspath(PROGRAM_FILE)==@__FILE__;check_sections();end
