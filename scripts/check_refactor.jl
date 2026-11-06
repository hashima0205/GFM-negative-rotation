# Regression fixtures were evaluated by the source code at the recorded base commit.
include(joinpath(@__DIR__,"../src/study.jl"))
function main()
    reference=TOML.parsefile(joinpath(ROOT,"provenance/refactor_reference.toml"))
    rows=Dict(r["case"]=>r for r in readcases(joinpath(ROOT,"inputs/cases.csv")))
    worst=0.;voltage_error=0.
    for sample in reference["samples"]
        row=rows[sample["case"]];c=load_config(joinpath(ROOT,"inputs",row["config"]),row);s=make_stage(c,sample["stage"])
        y=Float64.(sample["state"]);dy=zeros(length(y));rhs!(dy,y,s,0.)
        worst=max(worst,maximum(abs.(dy-Float64.(sample["rhs"]))))
        u=voltages(y,s);expected=complex.(sample["voltage_real"],sample["voltage_imag"])
        voltage_error=max(voltage_error,maximum(abs.(u-expected)))
    end
    @assert worst==0 && voltage_error==0
    classification_checks=[]
    for row in values(rows)
        folder=joinpath(ROOT,"results",row["case"]);verify_reference(folder)
        c=load_config(joinpath(ROOT,"inputs",row["config"]),row);s=make_stage(c,"post")
        target=vec(readdlm(joinpath(folder,"post_root.csv"),',',Float64))
        # Read only angle/frequency columns from the saved native states, preserving
        # their exact decimal representations and every timestamp used by classify.
        times=Float64[];states=Vector{Float64}[]
        open(`gzip -dc $(joinpath(folder,"states.csv.gz"))`) do io
            header=split(readline(io),',');positions=[findfirst(==("x$i"),header) for i in vcat(stateindices(:angle),stateindices(:frequency))]
            for line in eachline(io)
                values=split(line,',');values[3]=="post" || continue
                y=zeros(c.control=="VSM" ? 56 : 52)
                y[vcat(stateindices(:angle),stateindices(:frequency))]=parse.(Float64,values[positions])
                push!(times,parse(Float64,values[2]));push!(states,y)
            end
        end
        actual=classify(times,states,s,target);expected=readdlm(joinpath(folder,"machines.csv"),',',Any;skipstart=1)
        @assert [a[2] for a in actual]==String.(expected[:,2])
        metrics_error=maximum(maximum(abs.(Float64.(collect(a[3:end]))-Float64.(expected[j,3:end]))) for (j,a) in enumerate(actual))
        @assert metrics_error<1e-12
        push!(classification_checks,Dict("case"=>row["case"],"saved_samples"=>length(times),"all_machine_labels_equal"=>true,"max_classification_metric_error"=>metrics_error))
    end
    report=Dict("base_commit"=>reference["base_commit"],"rhs_samples"=>length(reference["samples"]),"max_rhs_error"=>worst,"max_voltage_error"=>voltage_error,"classifications"=>classification_checks)
    open(joinpath(validation_output(),"refactor_regression.toml"),"w") do io;TOML.print(io,report);end
    println("REFACTOR_REGRESSION_PASSED ",report)
end
if abspath(PROGRAM_FILE)==@__FILE__;main();end
