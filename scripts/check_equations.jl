include(joinpath(@__DIR__,"../src/study.jl"))
function main()
    verify_reference(joinpath(ROOT,"results",first(STUDY["cases"]["main"])))
    function row(control,mp,tau,d1=0,d2=0)
     Dict("control"=>control,"mp"=>string(mp),"taup"=>string(tau),"H"=>"2.5","D1"=>string(d1),"D2"=>string(d2),"omega_d"=>"50")
    end
    for (name,d1) in [("C",0),("C_D1_10",10)]
     c=load_config(joinpath(ROOT,"inputs/common.toml"),row("VSM",.05,.25,d1,100))
     a=readdlm(joinpath(ROOT,"provenance/reference_results",name*"_samples.csv"),',',Any;skipstart=1)
     worst=0.;vel=0.
     for r in eachrow(a)
      s=make_stage(c,String(r[1]));x=Float64.(r[3:68]);f=Float64.(r[69:134]);z=Float64.(r[135:138])
      y=legacy_to_native(x,c;z);du=similar(y);rhs!(du,y,s,Float64(r[2]))
      expected=copy(f[DYN66])
      for j in 1:4
       k=13(j-1);expected[k+12]=-c.mp*expected[k+12]-(c.D1*y[k+12]+c.D2*(y[k+12]-z[j]))/(2c.H)
      end
      worst=max(worst,maximum(abs.(expected-du[1:52])))
      vel=max(vel,maximum(abs.(native_to_legacy(y,s)-x)))
     end
     println(name," RHS_MAX ",worst," STATE_RECONSTRUCTION_MAX ",vel)
     @assert worst<1e-7 && vel<1e-8
    end
    for (name,tau) in [("A",.02),("B",1.0)]
     c=load_config(joinpath(ROOT,"inputs/original_droop.toml"),row("Droop",.02,tau))
     for stage in ["pre","fault","post"]
      x=vec(readdlm(joinpath(ROOT,"provenance/reference_results","droop_original_"*name*"_"*stage*"_initial.csv"),',',Float64))
      s=make_stage(c,stage);y=legacy_to_native(x,c)
      er=maximum(abs.(native_to_legacy(y,s)-x))
      println("DROOP_",name," ",stage," ALG_RECONSTRUCTION ",er);@assert er<1e-8
     end
    end
    c=load_config(joinpath(ROOT,"inputs/common.toml"),row("Droop",.05,.02));s=make_stage(c,"pre")
    y=legacy_to_native(vec(readdlm(joinpath(ROOT,"inputs/pre_seed_legacy.csv"),',',Float64)),c)
    du=similar(y);rhs!(du,y,s,0.);println("PRE_ROOT_RESIDUAL ",maximum(abs.(du)))
    t=@elapsed for i in 1:10000;rhs!(du,y,s,0.);end
    println("RHS_us ",t*100)


    # Algebraic Droop/VSM coordinate equivalence, only when additional damping is absent.
    cd=load_config(joinpath(ROOT,"inputs/common.toml"),row("Droop",.05,.25))
    cv=load_config(joinpath(ROOT,"inputs/common.toml"),row("VSM",.05,.25,0,0))
    worst=0.0
    for stage in ["pre","fault","post"]
     sd=make_stage(cd,stage);sv=make_stage(cv,stage)
     for perturb in [-.05,0.,.05]
      x=vec(readdlm(joinpath(ROOT,"inputs/pre_seed_legacy.csv"),',',Float64))
      x[[14,29,44,65]].+=perturb
      yd=legacy_to_native(x,cd);yv=legacy_to_native(x,cv);fd=zeros(52);fv=zeros(56)
      rhs!(fd,yd,sd,0.);rhs!(fv,yv,sv,0.)
      fd[[12,25,38,51]].*=-.05
      worst=max(worst,maximum(abs.(fd-fv[1:52])))
     end
    end
    @assert worst<1e-9
    println("UNDAMPED_COORDINATE_EQUIVALENCE_RHS_MAX ",worst)
    mkpath(joinpath(validation_output()))
    open(joinpath(validation_output(),"equivalence.toml"),"w") do io
     TOML.print(io,Dict("max_rhs_error"=>worst,"droop_mp"=>.05,"droop_tau_p"=>.25,"vsm_H"=>2.5,"vsm_D1"=>0.,"vsm_D2"=>0.,"independent_physical_evidence"=>false))
    end
end
if abspath(PROGRAM_FILE)==@__FILE__;main();end
