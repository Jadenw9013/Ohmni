* BEH-REG-BUCK-DCS core subcircuit (behavioural COT buck; NOT a vendor model)
* fidelity: behavioural_approximation. Constant on-time control, tON = K*VOUT/VIN, valley trigger when sense < VSET.
* ports: vin gnd vout(power output, after inductor) vos(sense input) en(logic: >0.5 V enabled)
* K    : TPS62160 datasheet text "tON = 420 x (VOUT/VIN) ns" (TPS6213x 400 ns with FSW low)
* RHS, RLS : high / low side Rds(on) ohm;  IQ : quiescent current A;  VSET: regulation point of sense input
* RINJ : internal ripple-injection resistance (ASSUMPTION, ohm): comparator sees VOS + RINJ*IL; without it a pure-ceramic COT loop sub-harmonically oscillates (shown in B1 history)
* L, DCR : inductor (external part, included here so the DCM zero-current detect can see its current)
.subckt BUCKCORE vin gnd vout vos en params: K=420n RHS=0.4 RLS=0.16 VSET=3.3 IQ=17u RDIS=10 CSWP=100p L=2.2u DCR=0.05 RINJ=10m
Ben enl gnd V = 0.5*(1+tanh((v(en)-v(gnd)-1)/0.1))
Cq q gnd 1p ic=0
* regenerative term 0.5*q*(1-q)*(2q-1) makes the latch bistable (holds 0 or 1 when neither set nor reset)
Bq gnd q I = 1e-3*( 4*v(setc)*(1-v(q)) - 4*v(rstc)*v(q) + 0.5*v(q)*(1-v(q))*(2*v(q)-1) )
Bqd qd gnd V = 0.5*(1+tanh((v(q)-0.5)/0.05))
Bset setc gnd V = v(enl)*0.5*(1+tanh((VSET-v(vos)-RINJ*(v(vx)-v(vout))/DCR)/2m))*0.5*(1+tanh((0.15-v(vr))/20m))
Brst rstc gnd V = 0.5*(1+tanh((v(vr)-v(vout))/2m)) + (1-v(enl))
Cr vr gnd 1n ic=0
Bch gnd vr I = v(qd)*(1n/K)*(v(vin)-v(gnd)) - (1-v(qd))*v(vr)/RDIS
* switches as smooth behavioural conductances (G = s/Ron + 1 uS leakage); S-device hysteresis caused timestep failures
Bhs vin sw I = (v(vin)-v(sw))*(v(qd)/RHS + 1u)
* low side: synchronous rectifier that conducts only while SW is below GND (ideal-diode behaviour: DCM zero-current cutoff)
Bls sw gnd I = (v(sw)-v(gnd))*((1-v(qd))*v(enl)/RLS*0.5*(1+tanh(-(v(sw)-v(gnd))/5m)) + 1u)
Csw sw gnd {CSWP}
Rswd sw gnd 10Meg
Lx sw vx {L}
Rdcr vx vout {DCR}
Biq vin gnd I = IQ*v(enl)
.ends
