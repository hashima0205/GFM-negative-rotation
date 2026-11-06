include(joinpath(@__DIR__,"run.jl"))
rows=readcases(joinpath(ROOT,"inputs/cases.csv"));configs=[load_config(joinpath(ROOT,"inputs",r["config"]),r) for r in rows]
for c in configs[2:end]
 @assert c.lines==configs[1].lines && c.machines==configs[1].machines
 @assert (c.G,c.B,c.faultG,c.fault_on,c.clearing)==(configs[1].G,configs[1].B,configs[1].faultG,configs[1].fault_on,configs[1].clearing)
 for stage in ["pre","fault","post"];@assert make_stage(c,stage).Y==make_stage(configs[1],stage).Y;end
end
@assert [k for k in keys(rows[1]) if rows[1][k]!=rows[2][k]] |> Set == Set(["case","taup"])
@assert [k for k in keys(rows[3]) if rows[3][k]!=rows[4][k]] |> Set == Set(["case","D1"])
open(joinpath(ROOT,"results/validation/common_conditions.toml"),"w") do io
 TOML.print(io,Dict("all_four_cases_network_load_PQ_inner_controls_current_limit_events_equal"=>true,"A_B_changed_fields"=>["case label","taup"],"C_C_D1_10_changed_fields"=>["case label","D1"],"bus5_prefault_voltage_pu"=>abs(voltages(vec(readdlm(joinpath(ROOT,"results/C/pre_root.csv"),',',Float64)),make_stage(configs[3],"pre"))[5])))
end
println("COMMON_CONDITIONS_VERIFIED")
