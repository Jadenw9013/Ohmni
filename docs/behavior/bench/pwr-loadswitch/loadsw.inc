* BEH-PWR-LOADSWITCH behavioural load switch / power switch (behavioural_approximation, not a vendor model)
* ports: vin vout gnd en(logic, >1.0 V on) ; params: RON (ohm), ILIM (A, constant-current clamp), VUV (V, UVLO rising threshold), TON (s, enable-to-full-on time constant), RQOD (ohm quick output discharge, 0 = none)
* Pass element: smooth clamp I = (Vd/RON)/(1+(Vd/(RON*ILIM))^4)^0.25 : linear RON below ~0.7*ILIM, constant ~ILIM above. Reverse current is NOT blocked (real parts with reverse-current protection need an extra diode).
* gating g in [0,1]: g = enable AND (vin > VUV), first-order lag TON.
.subckt LOADSW vin vout gnd en params: RON=0.079 ILIM=10 VUV=2.54 TON=10u RQOD=0
Bgt gt gnd V = 0.5*(1+tanh((v(en)-v(gnd)-1)/0.05))*0.5*(1+tanh((v(vin)-v(gnd)-VUV)/0.005))
Rg gt gs 1k
Cg gs gnd {TON/1k}
Bpass vin vout I = v(gs)*((v(vin)-v(vout))/RON)/pow(1+pow(abs(v(vin)-v(vout))/(RON*ILIM),4),0.25) + (1-v(gs))*(v(vin)-v(vout))*1n
.ends
