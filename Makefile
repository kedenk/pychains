SUFFIXES:
.PRECIOUS: subjects/microjson.py

#2>/dev/null
Q=
R=1
extract_json: results/microjson.txt
	@echo done $@

results/%.txt: subjects/%.py | subjects
	env R=$(R) python3 gencmd.py $< $(Q)

extract_comp_urltools:
	python3 gencmd.py src/pygen-ex/pygen_ex/urltools.py "https://www.hello.world#fragment?q1=1"

subjects/%.py: | subjects
	wget -c 'https://raw.githubusercontent.com/vrthra/pygen_ex/master/pygen_ex/microjson.py' -O $@.tmp
	mv $@.tmp $@

subjects:; mkdir -p $@
