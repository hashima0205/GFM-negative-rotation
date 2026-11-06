include(joinpath(@__DIR__,"../src/study.jl"))
function main()
 options=Set(["--strict","--horizon","--output","--results"]);positionals=String[];i=1
 while i<=length(ARGS)
  if ARGS[i] in options;i+=ARGS[i]=="--strict" ? 1 : 2
  else;startswith(ARGS[i],"--") && error("Unknown option: "*ARGS[i]);push!(positionals,ARGS[i]);i+=1;end
 end
 file=joinpath(ROOT,"inputs",isempty(positionals) ? "cases.csv" : positionals[1]);selection=length(positionals)>1 ? split(positionals[2],',') : nothing
 strict="--strict" in ARGS;harg=findfirst(==("--horizon"),ARGS);horizon=harg===nothing ? nothing : parse(Float64,ARGS[harg+1])
 outarg=findfirst(==("--output"),ARGS);output=outarg===nothing ? joinpath(ROOT,"outputs/runs") : abspath(ARGS[outarg+1])
 rows=readcases(file)
 selection!==nothing && !issubset(Set(selection),Set(r["case"] for r in rows)) && error("Unknown case selection")
 for row in rows;selection!==nothing && !(row["case"] in selection) && continue;run_case(row;strict,horizon,output);end
end
if abspath(PROGRAM_FILE)==@__FILE__;main();end
