include(joinpath(@__DIR__,"fault_basins.jl"))
function check_frozen_sections()
    records=[];settings=TOML.parsefile(SECTION_INPUT);historical=Dict{String,Any}()
    for row in filter(r->r["case"] in ["A","B","C"],readcases(joinpath(ROOT,"inputs/cases.csv")))
        ctx=frozen_context(row);(;c,s,target,dir)=ctx
        files=sort(filter(p->endswith(p,".toml"),readdir(joinpath(dir,"points");join=true)))
        @assert length(files)==43
        maxstate=0.;maxcoord=0.;maxvoltage=0.;maxalg=0.;maxkinematic=0.;maxz=0.;labels=Dict{String,Int}()
        for file in files
            a=TOML.parsefile(file);y=Float64.(a["initial_native"]);yf=Float64.(a["final_native"])
            expected=frozen_section(target,s,a["theta_requested"],a["df_requested"])
            maxstate=max(maxstate,maximum(abs.(y-expected)))
            frozen=setdiff(eachindex(y),[25,26,38,39,51,52])
            @assert y[frozen]==target[frozen]
            theta,freq=phase_coordinates(y,s);maxcoord=max(maxcoord,abs(theta-a["theta_requested"]),abs(freq-a["df_requested"]))
            for (x,k) in [(y,"initial_bus_voltage_ri"),(yf,"final_bus_voltage_ri")]
                uu=voltages(x,s);stored=complex.([v[1] for v in a[k]],[v[2] for v in a[k]])
                maxvoltage=max(maxvoltage,maximum(abs.(uu-stored)))
                inj=zeros(ComplexF64,8)
                for j in 1:4;inj[BUS[j]]=complex(x[13(j-1)+4],x[13(j-1)+3]);end
                maxalg=max(maxalg,maximum(abs.((s.Y*uu-inj)[GFMModel.NONSLACK])))
                dx=zeros(length(x));rhs!(dx,x,s,0.)
                maxkinematic=max(maxkinematic,abs(sum(dx[[26,39,52]])/3-2pi*phase_coordinates(x,s)[2]))
            end
            c.control=="VSM" && (maxz=max(maxz,maximum(abs.(y[53:56]))))
            @assert a["horizon_s"]==settings["horizon_s"] && a["retcode"]=="Success"
            @assert isfile(replace(file,".toml"=>"_projection.csv.gz"))
            lab=a["classification"];labels[lab]=get(labels,lab,0)+1
        end
        @assert maxstate==0 && maxcoord<1e-10 && maxvoltage<1e-12 && maxalg<1e-10 && maxkinematic<1e-10 && maxz<1e-12
        push!(records,Dict("case"=>row["case"],"points"=>length(files),"max_initial_state_definition_error"=>maxstate,"max_coordinate_error"=>maxcoord,"max_reconstructed_voltage_error"=>maxvoltage,"max_algebraic_residual"=>maxalg,"max_angle_frequency_kinematic_error"=>maxkinematic,"max_initial_washout_z"=>maxz,"classifications"=>labels))
        if row["case"]=="C"
            oldrow=copy(row);oldrow["mp"]="0.1";oldrow["D1"]="10"
            oldc=load_config(joinpath(ROOT,"inputs",row["config"]),oldrow);olds=make_stage(oldc,"post")
            reference=readdlm(joinpath(ROOT,"provenance/reference_results/historical_D1_10_section.csv"),',',Any;skipstart=1)
            maxinitial=0.;maxrhs=0.;matches=0
            for rr in eachrow(reference)
                id=Int(rr[1]);a=TOML.parsefile(joinpath(dir,"points",lpad(id,3,'0')*".toml"));y=Float64.(a["initial_native"])
                maxinitial=max(maxinitial,maximum(abs.(y-Float64.(rr[3:end]))))
                f=zeros(length(y));fold=similar(f);rhs!(f,y,s,0.);rhs!(fold,y,olds,0.);maxrhs=max(maxrhs,maximum(abs.(f-fold)))
                matches+=a["classification"]==String(rr[2])
            end
            @assert maxinitial<1e-12 && maxrhs<1e-12 && matches==43
            historical=Dict("old_mp"=>oldc.mp,"old_D1"=>oldc.D1,"current_mp"=>c.mp,"current_D1"=>c.D1,"equal_effective_nominal_damping"=>1/c.mp+c.D1,"matched_labels"=>matches,"points"=>43,"max_initial_native_difference"=>maxinitial,"max_same_state_RHS_difference"=>maxrhs,"old_horizons"=>"30/100/300 s; new classification independently uses 1000 s")
        end
    end
    open(joinpath(ROOT,"results/validation/fault_basin_checks.toml"),"w") do io;TOML.print(io,Dict("cases"=>records,"historical_D1_10_vs_C"=>historical));end
    println("FROZEN_SECTION_CHECKS_OK ",records," HISTORICAL ",historical)
end
if abspath(PROGRAM_FILE)==@__FILE__;check_frozen_sections();end
