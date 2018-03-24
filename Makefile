SUFFIXES:

subjects=microjson urljava urlpy mathexpr
log=$(addsuffix .log,$(addprefix .o/,$(subjects)))
.precious:$(log)

python3=python3
pip3=pip3
#2>/dev/null
Q=
R=1

help:
	@echo $(MAKE) $(addprefix chains.,$(subjects))

clobber:
	rm -rf .pickled .o .e .tmp

.pickled .o .e:
	mkdir -p $@

ifdef DUMB_SEARCH
SEARCH_STRATEGY=DUMB_SEARCH=$(DUMB_SEARCH)
else
SEARCH_STRATEGY=
endif

ifdef PYTHON_OPT
SPECIALIZATION=PYTHON_OPT=$(PYTHON_OPT)
else
SPECIALIZATION=
endif


R=0
SEED=R=$(R)
ENV=$(SEED) $(SEARCH_STRATEGY) $(SPECIALIZATION)

.o/%.log: subjects/%.py | .o .e
	env $(ENV) $(python3) ./bin/mychains.py $< 1> $@.out
	mv $@.out $@

chains.%: .o/%.log; @:

req:
	$(pip3) install -r requirements.txt --user
